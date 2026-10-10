from django.test import SimpleTestCase

from karma.signals_bus import (
    KARMA_EVENT_HANDLERS,
    emit_karma,
    register_karma_event,
)


class KarmaSignalsBusTests(SimpleTestCase):
    def setUp(self):
        self.previous_handlers = KARMA_EVENT_HANDLERS.copy()
        KARMA_EVENT_HANDLERS.clear()

    def tearDown(self):
        KARMA_EVENT_HANDLERS.clear()
        KARMA_EVENT_HANDLERS.update(self.previous_handlers)

    def test_decorator_registers_and_returns_the_original_handler(self):
        @register_karma_event('item_resolved')
        def handle_item_resolved(**context):
            return context['user_id']

        self.assertIs(KARMA_EVENT_HANDLERS['item_resolved'], handle_item_resolved)
        self.assertEqual(emit_karma('item_resolved', user_id=7), 7)

    def test_event_context_is_forwarded_to_the_handler(self):
        received = {}

        @register_karma_event('peer_help')
        def handle_peer_help(**context):
            received.update(context)

        result = emit_karma(
            'peer_help',
            user_id=7,
            room_id='room-1',
            message_id='message-1',
        )

        self.assertIsNone(result)
        self.assertEqual(received, {
            'user_id': 7,
            'room_id': 'room-1',
            'message_id': 'message-1',
        })

    def test_unknown_event_is_a_noop(self):
        self.assertIsNone(emit_karma('future_event', user_id=7))

    def test_registering_a_kind_replaces_its_previous_handler(self):
        calls = []

        @register_karma_event('welcome')
        def first_handler(**context):
            calls.append('first')

        @register_karma_event('welcome')
        def second_handler(**context):
            calls.append('second')

        emit_karma('welcome', user_id=7)

        self.assertIs(KARMA_EVENT_HANDLERS['welcome'], second_handler)
        self.assertEqual(calls, ['second'])

    def test_empty_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            register_karma_event('   ')

    def test_non_callable_handler_is_rejected(self):
        with self.assertRaises(TypeError):
            register_karma_event('item_resolved')(object())

    def test_handler_errors_are_not_silently_swallowed(self):
        @register_karma_event('dm_item_ontime')
        def broken_handler(**context):
            raise RuntimeError('scoring failed')

        with self.assertRaisesRegex(RuntimeError, 'scoring failed'):
            emit_karma('dm_item_ontime', user_id=7)
