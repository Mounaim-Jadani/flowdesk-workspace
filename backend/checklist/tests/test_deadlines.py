from django.test import TestCase
from datetime import datetime, timedelta
from checklist.deadlines import resolve_deadline

class DeadlinesTests(TestCase):
    def setUp(self):
        # Mercredi 2 Septembre 2026 à 10:00:00
        self.now = datetime(2026, 9, 2, 10, 0, 0)
        
    def test_tonight(self):
        target = resolve_deadline("ce soir", self.now)
        self.assertEqual(target, datetime(2026, 9, 2, 20, 0, 0))
        
    def test_tomorrow(self):
        target = resolve_deadline("demain", self.now)
        self.assertEqual(target, datetime(2026, 9, 3, 18, 0, 0))
        
    def test_friday(self):
        # Le 2 Sept est un Mercredi. Le prochain Vendredi est le 4.
        target = resolve_deadline("vendredi", self.now)
        self.assertEqual(target, datetime(2026, 9, 4, 18, 0, 0))
        
    def test_monday(self):
        # Le prochain Lundi est le 7 Septembre
        target = resolve_deadline("monday", self.now)
        self.assertEqual(target, datetime(2026, 9, 7, 18, 0, 0))
        
    def test_delay_hours(self):
        target = resolve_deadline("in 3 hours", self.now)
        self.assertEqual(target, self.now + timedelta(hours=3))
        
    def test_delay_days(self):
        target = resolve_deadline("dans 5 jours", self.now)
        self.assertEqual(target, self.now + timedelta(days=5))
        
    def test_next_week(self):
        # La semaine prochaine (On fixe ça au prochain Lundi à 18h)
        target = resolve_deadline("la semaine prochaine", self.now)
        self.assertEqual(target, datetime(2026, 9, 7, 18, 0, 0))
        
    def test_explicit_date(self):
        # Date standard : 20 Septembre (dans le futur cette année)
        target = resolve_deadline("20/09", self.now)
        self.assertEqual(target, datetime(2026, 9, 20, 18, 0, 0))
        
    def test_explicit_date_past(self):
        # Date passée sans année explicite : on assume que c'est l'année suivante
        target = resolve_deadline("01/09", self.now)
        self.assertEqual(target, datetime(2027, 9, 1, 18, 0, 0))
        
    def test_explicit_date_year(self):
        # Date avec année explicite
        target = resolve_deadline("05/10/2026", self.now)
        self.assertEqual(target, datetime(2026, 10, 5, 18, 0, 0))
