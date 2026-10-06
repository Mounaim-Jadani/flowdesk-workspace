from django.test import TestCase
from checklist.engine import detect_commitment

class EngineTests(TestCase):
    def test_positive_fr_1(self):
        # 1. Positifs FR
        result = detect_commitment("ok, je prépare le doc pour demain")
        self.assertIsNotNone(result)
        self.assertTrue(result['is_commitment'])
        self.assertEqual(result['deadline_raw'], 'demain')
        self.assertEqual(result['confidence'], 0.8)
        self.assertEqual(result['mentioned'], [])

    def test_positive_en_1(self):
        # 2. Positifs EN
        result = detect_commitment("I'll send it tomorrow")
        self.assertIsNotNone(result)
        self.assertTrue(result['is_commitment'])
        self.assertEqual(result['deadline_raw'], 'tomorrow')

    def test_positive_complex_1(self):
        # 3. Positifs complexes
        result = detect_commitment("je m'en occupe @alice vendredi")
        self.assertIsNotNone(result)
        self.assertTrue(result['is_commitment'])
        self.assertEqual(result['deadline_raw'], 'vendredi')
        self.assertEqual(result['mentioned'], ['alice'])
        self.assertEqual(result['confidence'], 0.9)

    def test_negative_basic_1(self):
        # 4. Négatifs basiques
        result = detect_commitment("ça va ?")
        self.assertIsNone(result)

    def test_false_positive_avoided_1(self):
        # 5. Faux positifs évités (exclusion passée)
        result = detect_commitment("hier j'ai fait ça et aujourd'hui je prépare la suite")
        self.assertIsNone(result)

    def test_false_positive_avoided_2(self):
        # 6. Faux positifs évités (exclusion conditionnelle)
        result = detect_commitment("il faudrait que je prépare le rapport")
        self.assertIsNone(result)

    def test_mention_without_commitment(self):
        # 7. Mention sans engagement
        result = detect_commitment("@bob tu en penses quoi ?")
        self.assertIsNone(result)

    def test_deadline_without_commitment(self):
        # 8. Échéance sans engagement
        result = detect_commitment("on se voit vendredi")
        self.assertIsNone(result)

    def test_positive_no_deadline_no_mention(self):
        # 9. Juste un engagement
        result = detect_commitment("pas de soucis, je vais faire le nécessaire")
        self.assertIsNotNone(result)
        self.assertTrue(result['is_commitment'])
        self.assertIsNone(result['deadline_raw'])
        self.assertEqual(result['mentioned'], [])
        self.assertEqual(result['confidence'], 0.6)

    def test_positive_mention_only(self):
        # 10. Engagement avec mention mais sans date
        result = detect_commitment("je t'envoie le fichier @charlie")
        self.assertIsNotNone(result)
        self.assertTrue(result['is_commitment'])
        self.assertIsNone(result['deadline_raw'])
        self.assertEqual(result['mentioned'], ['charlie'])
        self.assertEqual(result['confidence'], 0.9)

    def test_request_with_named_recipient_is_detected(self):
        result = detect_commitment("Bob, peux-tu vérifier l'API avant demain ?")
        self.assertIsNotNone(result)
        self.assertTrue(result['is_commitment'])
        self.assertEqual(result['deadline_raw'], 'demain')
        self.assertEqual(result['mentioned'], ['bob'])
        self.assertEqual(result['confidence'], 0.9)

    def test_request_with_at_mention_is_detected(self):
        result = detect_commitment("@bob, peux-tu préparer le budget vendredi ?")
        self.assertIsNotNone(result)
        self.assertEqual(result['mentioned'], ['bob'])
