from django.contrib.auth import get_user_model
from django.test import TestCase

from karma.badges import check_badges
from karma.models import Badge, KarmaEvent


class KarmaBadgeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='badge-user@example.com', username='badge-user', password='test-password'
        )

    def test_problem_solver_badge_unlocks_at_ten_group_resolutions(self):
        KarmaEvent.objects.bulk_create([
            KarmaEvent(
                user=self.user,
                kind='item_resolved',
                score=10,
                metadata={'room_type': 'group'},
                source_key=f'group-item-{index}',
            )
            for index in range(10)
        ])

        self.assertEqual(check_badges(self.user.id), ['problem_solver'])
        self.assertTrue(Badge.objects.filter(user=self.user, kind='problem_solver').exists())
        self.assertEqual(check_badges(self.user.id), [])
        self.assertEqual(Badge.objects.filter(user=self.user, kind='problem_solver').count(), 1)

    def test_reliable_partner_badge_unlocks_at_five_on_time_dm_items(self):
        KarmaEvent.objects.bulk_create([
            KarmaEvent(
                user=self.user,
                kind='dm_item_ontime',
                score=6,
                metadata={'room_type': 'direct'},
                source_key=f'dm-item-{index}',
            )
            for index in range(5)
        ])

        self.assertEqual(check_badges(self.user.id), ['reliable_partner'])
        self.assertTrue(Badge.objects.filter(user=self.user, kind='reliable_partner').exists())
