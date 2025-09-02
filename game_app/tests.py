from django.test import TestCase
from django.utils import timezone
from .models import Player, BoostType, Boost, PlayerBoostHistory
from django.core.exceptions import ValidationError
from datetime import timedelta


class PlayerModelTest(TestCase):
    #тест для игрока
    
    def setUp(self):
        self.player_data = {
            'username': 'test_player',
            'email': 'test@example.com'
        }
    
    def test_player_creation(self):
        #тест создания юзера
        player = Player.objects.create(**self.player_data)
        
        self.assertEqual(player.username, 'test_player')
        self.assertEqual(player.email, 'test@example.com')
        self.assertEqual(player.login_count, 0)
        self.assertEqual(player.daily_points, 0)
        self.assertEqual(player.total_points, 0)
        self.assertIsNone(player.first_login)
        self.assertIsNone(player.last_login)
    
    def test_player_str_method(self):
        player = Player.objects.create(**self.player_data)
        self.assertEqual(str(player), 'test_player')
    
    def test_first_login_tracking(self):
        #для первого входа
        player = Player.objects.create(**self.player_data)
        
        player.record_login()
        
        self.assertIsNotNone(player.first_login)
        self.assertIsNotNone(player.last_login)
        self.assertEqual(player.login_count, 1)
        self.assertEqual(player.daily_points, 10)
        self.assertEqual(player.total_points, 10)
        
        first_login_time = player.first_login
        
        #второй вход
        player.record_login()
        
        #первый вход не должен меняться
        self.assertEqual(player.first_login, first_login_time)
        self.assertEqual(player.login_count, 2)
        self.assertEqual(player.daily_points, 20)
        self.assertEqual(player.total_points, 20)
    
    def test_daily_points_accumulation(self):
        #тест накопления баллов ежедневных
        player = Player.objects.create(**self.player_data)
        
        #несколько входов
        for i in range(5):
            player.record_login()
        
        self.assertEqual(player.login_count, 5)
        self.assertEqual(player.daily_points, 50)
        self.assertEqual(player.total_points, 50)


class BoostTypeModelTest(TestCase):
    
    def setUp(self):
        self.boost_type_data = {
            'name': 'speed',
            'description': 'Увеличивает скорость движения',
            'duration_minutes': 30,
            'multiplier': 2.0
        }
    
    def test_boost_type_creation(self):
        #типы бустов
        boost_type = BoostType.objects.create(**self.boost_type_data)
        
        self.assertEqual(boost_type.name, 'speed')
        self.assertEqual(boost_type.description, 'Увеличивает скорость движения')
        self.assertEqual(boost_type.duration_minutes, 30)
        self.assertEqual(boost_type.multiplier, 2.0)
    
    def test_boost_type_str_method(self):
        boost_type = BoostType.objects.create(**self.boost_type_data)
        self.assertEqual(str(boost_type), 'Speed Boost')
    
    def test_boost_type_choices(self):
        #доступные бусты
        valid_types = ['speed', 'damage', 'health', 'experience', 'coins']
        
        for boost_type in valid_types:
            bt = BoostType.objects.create(
                name=boost_type,
                description=f'Test {boost_type} boost'
            )
            self.assertIn(boost_type, [choice[0] for choice in BoostType.BOOST_TYPES])


class BoostModelTest(TestCase):
    
    def setUp(self):
        self.player = Player.objects.create(
            username='test_player',
            email='test@example.com'
        )
        self.boost_type = BoostType.objects.create(
            name='speed',
            description='Speed boost',
            duration_minutes=60,
            multiplier=2.0
        )
    
    def test_boost_creation(self):
        #создание буста
        boost = Boost.objects.create(
            player=self.player,
            boost_type=self.boost_type,
            quantity=3,
            source='level_completion',
            level_earned=5
        )
        
        self.assertEqual(boost.player, self.player)
        self.assertEqual(boost.boost_type, self.boost_type)
        self.assertEqual(boost.quantity, 3)
        self.assertEqual(boost.source, 'level_completion')
        self.assertEqual(boost.level_earned, 5)
        self.assertFalse(boost.is_active)
        self.assertIsNone(boost.used_at)
        self.assertIsNone(boost.expires_at)
    
    def test_boost_str_method(self):
        boost = Boost.objects.create(
            player=self.player,
            boost_type=self.boost_type,
            quantity=2,
            source='manual'
        )
        expected_str = f"{self.player.username} - {self.boost_type.name} x2"
        self.assertEqual(str(boost), expected_str)
    
    def test_boost_activation(self):
        #активация буста
        boost = Boost.objects.create(
            player=self.player,
            boost_type=self.boost_type,
            quantity=1,
            source='manual'
        )
        
        
        result = boost.activate()
        
        self.assertTrue(result)
        self.assertTrue(boost.is_active)
        self.assertEqual(boost.quantity, 0)  
        self.assertIsNotNone(boost.used_at)
        self.assertIsNotNone(boost.expires_at)
        
        #проверяем время истечения
        expected_expiry = boost.used_at + timedelta(minutes=self.boost_type.duration_minutes)
        self.assertEqual(boost.expires_at.replace(microsecond=0), 
                        expected_expiry.replace(microsecond=0))
    
    def test_boost_activation_without_quantity(self):
        #проверка буста без нужного количества
        boost = Boost.objects.create(
            player=self.player,
            boost_type=self.boost_type,
            quantity=0,  #нет бустов
            source='manual'
        )
        
        result = boost.activate()
        
        self.assertFalse(result)
        self.assertFalse(boost.is_active)
        self.assertIsNone(boost.used_at)
        self.assertIsNone(boost.expires_at)
    
    def test_boost_expiration_check(self):
        #проверка истечения буста
        boost = Boost.objects.create(
            player=self.player,
            boost_type=self.boost_type,
            quantity=1,
            source='manual'
        )
        
        boost.activate()
        
        #время истечения в прошлом
        boost.expires_at = timezone.now() - timedelta(minutes=1)
        boost.save()
        
        #проверка истечения
        is_expired = boost.is_expired()
        
        self.assertTrue(is_expired)
        self.assertFalse(boost.is_active)  #должен стать неактивным
    
    def test_award_boost_for_level(self):
        #начисление буста за прохождение уровня
        boost = Boost.award_boost_for_level(
            player=self.player,
            boost_type=self.boost_type,
            level_number=10,
            quantity=2
        )
        
        self.assertEqual(boost.player, self.player)
        self.assertEqual(boost.boost_type, self.boost_type)
        self.assertEqual(boost.quantity, 2)
        self.assertEqual(boost.source, 'level_completion')
        self.assertEqual(boost.level_earned, 10)
    
    def test_award_boost_manually(self):
        #ручное начисление
        boost = Boost.award_boost_manually(
            player=self.player,
            boost_type=self.boost_type,
            quantity=5
        )
        
        self.assertEqual(boost.player, self.player)
        self.assertEqual(boost.boost_type, self.boost_type)
        self.assertEqual(boost.quantity, 5)
        self.assertEqual(boost.source, 'manual')
        self.assertIsNone(boost.level_earned)


class PlayerBoostHistoryModelTest(TestCase):
    
    def setUp(self):
        self.player = Player.objects.create(
            username='test_player',
            email='test@example.com'
        )
        self.boost_type = BoostType.objects.create(
            name='damage',
            description='Damage boost',
            duration_minutes=30
        )
    
    def test_boost_history_creation(self):
        #запись бустов
        activated_time = timezone.now()
        expired_time = activated_time + timedelta(minutes=30)
        
        history = PlayerBoostHistory.objects.create(
            player=self.player,
            boost_type=self.boost_type,
            activated_at=activated_time,
            expired_at=expired_time,
            level_used=15
        )
        
        self.assertEqual(history.player, self.player)
        self.assertEqual(history.boost_type, self.boost_type)
        self.assertEqual(history.activated_at, activated_time)
        self.assertEqual(history.expired_at, expired_time)
        self.assertEqual(history.level_used, 15)


class IntegrationTest(TestCase):
    def setUp(self):
        self.player = Player.objects.create(
            username='integration_player',
            email='integration@example.com'
        )
        self.speed_boost = BoostType.objects.create(
            name='speed',
            description='Speed boost',
            duration_minutes=60
        )
        self.damage_boost = BoostType.objects.create(
            name='damage',
            description='Damage boost',
            duration_minutes=30
        )
    
    def test_complete_player_workflow(self):
        #полный процесс
        #вход в игру
        self.player.record_login()
        self.assertEqual(self.player.login_count, 1)
        self.assertIsNotNone(self.player.first_login)
        
        #бонус за прохождение уровня
        speed_boost = Boost.award_boost_for_level(
            player=self.player,
            boost_type=self.speed_boost,
            level_number=5,
            quantity=2
        )
        
        damage_boost = Boost.award_boost_manually(
            player=self.player,
            boost_type=self.damage_boost,
            quantity=1
        )
        
        #проверка создания бустов
        player_boosts = Boost.objects.filter(player=self.player)
        self.assertEqual(player_boosts.count(), 2)
        
        #активация бустов
        speed_boost.activate()
        self.assertTrue(speed_boost.is_active)
        self.assertEqual(speed_boost.quantity, 1) 
        
        #проверка неактивированного буста
        self.assertFalse(damage_boost.is_active)
        self.assertEqual(damage_boost.quantity, 1)
    
    def test_multiple_players_boosts(self):
        #еще один игрок
        player2 = Player.objects.create(
            username='player2',
            email='player2@example.com'
        )
        
        #бусты игрокам
        boost1 = Boost.award_boost_for_level(
            player=self.player,
            boost_type=self.speed_boost,
            level_number=1
        )
        
        boost2 = Boost.award_boost_for_level(
            player=player2,
            boost_type=self.speed_boost,
            level_number=1
        )
        
        #бусты правильно активировались
        self.assertEqual(boost1.player, self.player)
        self.assertEqual(boost2.player, player2)
        
        #проверка бустов у игрока
        player1_boosts = Boost.objects.filter(player=self.player)
        player2_boosts = Boost.objects.filter(player=player2)
        
        self.assertEqual(player1_boosts.count(), 1)
        self.assertEqual(player2_boosts.count(), 1)