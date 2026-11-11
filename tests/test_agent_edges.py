"""Các nhánh lỗi của loop; không gọi API hay sửa fixture."""
import json
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import patch

from agent import _retry_delay, run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class AgentEdgeTests(unittest.TestCase):
    def test_provider_exception_does_not_leak_exception_body(self):
        class BrokenProvider:
            def complete(self, messages, schemas):
                raise RuntimeError('private-request-body')

        result = run_agent('Kiểm tra', BrokenProvider(), StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['trace'][0]['event'], 'provider_error')
        self.assertNotIn('private-request-body', json.dumps(result))

    def test_tool_exception_becomes_an_observation(self):
        class BrokenTools:
            def execute(self, name, args):
                raise TimeoutError('temporary failure')

        model = FakeProvider([
            tool_call('t', 'get_status', '{"provider":"github"}'),
            final('Chưa xác nhận được trạng thái.'),
        ])
        result = run_agent('Kiểm tra', model, BrokenTools())
        observation = json.loads(model.histories[1][-1]['content'])
        self.assertEqual(observation['error'], 'TimeoutError')
        self.assertEqual(result['status'], 'completed')

    def test_array_arguments_are_rejected(self):
        model = FakeProvider([tool_call('t', 'get_status', '[]'), final('Thiếu tham số.')])
        run_agent('Kiểm tra', model, StatusTools())
        self.assertEqual(json.loads(model.histories[1][-1]['content'])['error'], 'INVALID_ARGUMENTS')

    def test_bad_first_call_does_not_skip_the_second(self):
        response = tool_call('bad', 'get_status', '{')
        good = tool_call('good', 'get_status', '{"provider":"github"}')
        response['calls'] += good['calls']
        response['message']['tool_calls'] += good['message']['tool_calls']
        model = FakeProvider([response, final('Đã kiểm tra phần hợp lệ.')])
        result = run_agent('Kiểm tra', model, StatusTools())
        returned = model.histories[1][-2:]
        self.assertEqual([message['tool_call_id'] for message in returned], ['bad', 'good'])
        self.assertEqual(json.loads(returned[0]['content'])['error'], 'INVALID_ARGUMENTS')
        self.assertEqual(json.loads(returned[1]['content'])['provider'], 'github')
        self.assertEqual(result['status'], 'completed')

    def test_original_assistant_message_is_kept(self):
        response = tool_call('t', 'get_status', '{"provider":"github"}')
        response['message']['content'] = 'Tôi sẽ kiểm tra.'
        model = FakeProvider([response, final()])
        run_agent('Kiểm tra', model, StatusTools())
        self.assertEqual(model.histories[1][-2], response['message'])

    def test_empty_or_abnormal_final_is_not_completed(self):
        for response in [final(''), dict(final('Bị cắt.'), finish='length'),
                         dict(final(), finish='content_filter'), dict(final(), finish='tool_calls')]:
            with self.subTest(response=response):
                result = run_agent('Kiểm tra', FakeProvider([response]), StatusTools())
                self.assertEqual(result['status'], 'error')

    def test_invalid_budget_does_not_call_the_provider(self):
        for budget in [0, -1, True, 1.5]:
            with self.subTest(budget=budget):
                model = FakeProvider([])
                result = run_agent('Kiểm tra', model, StatusTools(), max_steps=budget)
                self.assertEqual(result['status'], 'error')
                self.assertEqual(model.histories, [])

    def test_usage_is_preserved_per_model_call(self):
        response = final()
        response['usage'] = {'prompt_tokens': 10, 'completion_tokens': 4, 'cost': 0.001}
        result = run_agent('Kiểm tra', FakeProvider([response]), StatusTools())
        self.assertEqual(result['usage'], [response['usage']])

    def test_bad_provider_type_still_reaches_tool_validation(self):
        model = FakeProvider([tool_call('t', 'get_status', '{"provider":[]}'), final('Thiếu dữ liệu.')])
        result = run_agent('Kiểm tra', model, StatusTools())
        self.assertEqual(result['status'], 'completed')
        self.assertFalse(json.loads(model.histories[1][-1]['content'])['ok'])

    def test_source_check_covers_both_parallel_incidents(self):
        class Tools:
            def execute(self, name, args):
                return {'ok': True, 'url': 'https://status.example/incidents/' + args['incident_id']}

        response = tool_call('a', 'get_incident_details', '{"incident_id":"first"}')
        second = tool_call('b', 'get_incident_details', '{"incident_id":"second"}')
        response['calls'] += second['calls']
        response['message']['tool_calls'] += second['message']['tool_calls']
        first_url = 'https://status.example/incidents/first'
        second_url = 'https://status.example/incidents/second'
        model = FakeProvider([response, final(first_url), final(first_url + ' ' + second_url)])
        result = run_agent('So sánh', model, Tools(), max_steps=3)
        self.assertEqual(result['status'], 'completed')
        event = next(row for row in result['trace'] if row['event'] == 'validation_missing_source')
        self.assertEqual(event['missing_urls'], [second_url])


class RateLimitTests(unittest.TestCase):
    def test_long_retry_after_stops_without_sleep_or_second_request(self):
        class Tools:
            calls = 0

            def execute(self, name, args):
                self.calls += 1
                return {'ok': False, 'error': 'RATE_LIMITED', 'retry_after': '120'}

        tools = Tools()
        model = FakeProvider([tool_call('a', 'get_status', '{}'),
                              tool_call('b', 'get_status', '{}'), final('Chưa xác nhận được.')])
        with patch('agent.time.sleep') as sleep:
            result = run_agent('Kiểm tra', model, tools)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(tools.calls, 1)
        sleep.assert_not_called()
        self.assertTrue(json.loads(model.histories[2][-1]['content'])['retry_stopped'])

    def test_persistent_429_is_bounded_even_if_model_keeps_retrying(self):
        class Tools:
            calls = 0

            def execute(self, name, args):
                self.calls += 1
                return {'ok': False, 'error': 'RATE_LIMITED', 'retry_after_seconds': 0}

        tools = Tools()
        responses = [tool_call(str(i), 'get_status', '{}') for i in range(4)] + [final('Không lấy được dữ liệu.')]
        result = run_agent('Kiểm tra', FakeProvider(responses), tools)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(tools.calls, 3)
        attempts = [row for row in result['trace'] if row['event'] == 'tool']
        self.assertEqual(len(attempts), 4)  # Giữ cả lần model yêu cầu nhưng code đã chặn.
        self.assertTrue(attempts[-1]['result']['retry_stopped'])

    def test_short_retry_after_is_respected(self):
        class Tools:
            calls = 0

            def execute(self, name, args):
                self.calls += 1
                if self.calls == 1:
                    return {'ok': False, 'error': 'RATE_LIMITED', 'retry_after': '1'}
                return {'provider': 'github', 'overall': {'indicator': 'none'}}

        model = FakeProvider([tool_call('a', 'get_status', '{}'),
                              tool_call('b', 'get_status', '{}'), final('Đã lấy được dữ liệu.')])
        with patch('agent.time.sleep') as sleep:
            result = run_agent('Kiểm tra', model, Tools())
        self.assertEqual(result['status'], 'completed')
        sleep.assert_called_once_with(1.0)

    def test_retry_after_accepts_http_date_and_rejects_nonfinite_values(self):
        date = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=120))
        seconds = _retry_delay({'retry_after': date})
        self.assertGreater(seconds, 118)
        self.assertLessEqual(seconds, 121)
        self.assertGreater(_retry_delay({'retry_after': 'inf'}), 2)
        self.assertEqual(_retry_delay({'retry_after': 'invalid'}), 0)
