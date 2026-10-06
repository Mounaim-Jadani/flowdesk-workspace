from django.test import SimpleTestCase
import json
import os
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from digest.generator import _rule_reply_count, _rule_urgent, _rule_time_gaps, build_digest

class GeneratorTests(SimpleTestCase):

    def test_rule_reply_count(self):
        messages = [
            {'id': 1, 'content': 'Hello'},
            {'id': 2, 'content': 'Hi', 'reply_to_id': 1},
            {'id': 3, 'content': 'Yes', 'reply_to_id': 1},
            {'id': 4, 'content': 'Yo', 'reply_to_id': 2}
        ]
        res = _rule_reply_count(messages)
        self.assertEqual(len(res), 2)
        # Message 1 has 2 replies, Message 2 has 1 reply
        self.assertEqual(res[0]['id'], 1)
        self.assertEqual(res[1]['id'], 2)

    def test_rule_reply_count_empty(self):
        self.assertEqual(_rule_reply_count([]), [])

    def test_rule_urgent_keyword(self):
        messages = [
            {'id': 1, 'content': 'This is URGENT please'},
            {'id': 2, 'content': 'Just a normal message'}
        ]
        res = _rule_urgent(messages)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['id'], 1)

    def test_rule_urgent_flag(self):
        messages = [
            {'id': 1, 'content': 'Something', 'is_urgent': True},
            {'id': 2, 'content': 'Else', 'is_urgent': False}
        ]
        res = _rule_urgent(messages)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['id'], 1)

    def test_rule_time_gaps_mono_subject(self):
        messages = [
            {'id': 1, 'created_at': '2026-09-29T10:00:00Z'},
            {'id': 2, 'created_at': '2026-09-29T10:05:00Z'},
            {'id': 3, 'created_at': '2026-09-29T10:10:00Z'}
        ]
        res = _rule_time_gaps(messages)
        # Only the first message is returned
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['id'], 1)

    def test_rule_time_gaps_multi_subject(self):
        messages = [
            {'id': 1, 'created_at': '2026-09-29T10:00:00Z'},
            {'id': 2, 'created_at': '2026-09-29T13:05:00Z'}, # Gap of > 2h
            {'id': 3, 'created_at': '2026-09-29T13:10:00Z'}
        ]
        res = _rule_time_gaps(messages)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['id'], 1)
        self.assertEqual(res[1]['id'], 2)

    def test_build_digest_mentions_cap(self):
        messages = [
            {'id': 1, 'content': '@bob hey', 'created_at': '2026-09-29T10:00:00Z'},
            {'id': 2, 'content': '@bob yo', 'created_at': '2026-09-29T10:01:00Z'},
            {'id': 3, 'content': '@bob test', 'created_at': '2026-09-29T10:02:00Z'},
            {'id': 4, 'content': '@bob again', 'created_at': '2026-09-29T10:03:00Z'},
            {'id': 5, 'content': '@bob last', 'created_at': '2026-09-29T10:04:00Z'}
        ]
        digest = build_digest(messages, {'username': 'bob'}, '2026-09-29', '2026-09-30')
        # Should be capped at 4 most recent mentions
        self.assertEqual(len(digest['mentions']), 4)
        # Most recent is id 5
        self.assertEqual(digest['mentions'][0]['message_id'], '5')

    def test_build_digest_stats(self):
        messages = [
            {'id': 1, 'sender_username': 'alice'},
            {'id': 2, 'sender_username': 'bob'},
            {'id': 3, 'sender_username': 'alice'}
        ]
        digest = build_digest(messages, {'username': 'bob'}, '2026-09-29', '2026-09-30')
        self.assertEqual(digest['stats']['message_count'], 3)
        self.assertEqual(digest['stats']['participants'], 2)
        self.assertEqual(digest['stats']['decisions_count'], 0)
        self.assertEqual(digest['stats']['open_items'], 0)

    def test_local_group_fallback_keeps_speaker_names(self):
        digest = build_digest(
            [
                {'id': '1', 'sender_username': 'alice', 'content': 'Je prépare le mariage.'},
                {'id': '2', 'sender_username': 'bob', 'content': 'Toi, tu dois confirmer la salle.'},
            ],
            {'username': 'alice'},
            'since',
            'until',
            chat_type='group',
        )
        self.assertIn('alice : Je prépare le mariage.', digest['summary'])
        self.assertIn('bob : Toi, tu dois confirmer la salle.', digest['summary'])


@patch.dict(os.environ, {'GROQ_API_KEY': 'test-only-key'}, clear=True)
class GroqDigestTests(SimpleTestCase):
    messages = [
        {'id': 'm1', 'content': 'La salle doit être confirmée vendredi.',
         'sender_username': 'alice', 'created_at': '2026-10-05T12:00:00Z'},
        {'id': 'm2', 'content': 'Nous prévoyons 120 invités.',
         'sender_username': 'alice', 'created_at': '2026-10-05T12:01:00Z'},
    ]

    def response(self, content):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            'choices': [{'message': {'content': json.dumps(content)}}],
        }).encode()
        return response

    @patch('digest.generator.urllib.request.urlopen')
    def test_provider_uses_explicit_user_agent_and_falls_back_on_http_error(self, urlopen):
        urlopen.side_effect = [
            HTTPError('https://api.groq.com', 429, 'Rate limited', {}, None),
            self.response({'summary': 'Je prépare mon mariage avec 120 invités ; la salle reste à confirmer.',
                           'key_points': [{'message_id': 'm1', 'text': 'Confirmer la salle vendredi.'},
                                          {'message_id': 'invented-id', 'text': 'Invented'}]}),
        ]
        digest = build_digest(self.messages, {'username': 'bob'}, 'since', 'until',
                              lang_pref='french', use_ai=True)
        requests = [call.args[0] for call in urlopen.call_args_list]
        self.assertEqual([json.loads(request.data)['model'] for request in requests],
                         ['openai/gpt-oss-120b', 'allam-2-7b'])
        self.assertEqual(requests[0].get_header('User-agent'), 'FlowDesk/1.0')
        self.assertEqual(digest['stats']['summary_model'], 'allam-2-7b')
        self.assertEqual([point['message_id'] for point in digest['key_points']], ['m1'])
        self.assertEqual(digest['key_points'][0]['username'], 'alice')
        self.assertEqual(digest['stats']['summary_prompt_version'], 'speaker-voice-v3')

    @patch('digest.generator.urllib.request.urlopen')
    def test_arabic_tries_three_models_before_local_fallback(self, urlopen):
        urlopen.side_effect = HTTPError('https://api.groq.com', 503, 'Unavailable', {}, None)
        digest = build_digest(self.messages, {}, 'since', 'until', lang_pref='fusha', use_ai=True)
        models = [json.loads(call.args[0].data)['model'] for call in urlopen.call_args_list]
        self.assertEqual(models, ['allam-2-7b', 'qwen/qwen3.8-27b', 'openai/gpt-oss-120b'])
        self.assertEqual(digest['stats']['summary_model'], 'local-heuristic')

    @patch('digest.generator.urllib.request.urlopen')
    def test_malformed_summary_tries_next_model(self, urlopen):
        urlopen.side_effect = [self.response({'summary': None}),
                              self.response({'summary': 'أنا أتابع تفاصيل المحادثة وأحتاج إلى تأكيد الخطوة القادمة.', 'key_points': []})]
        digest = build_digest(self.messages, {}, 'since', 'until', lang_pref='fusha', use_ai=True)
        self.assertEqual(digest['summary'], 'أنا أتابع تفاصيل المحادثة وأحتاج إلى تأكيد الخطوة القادمة.')
        self.assertEqual(digest['stats']['summary_model'], 'qwen/qwen3.8-27b')
