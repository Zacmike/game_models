from django.db import models
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
import csv
import io


# Первое задание

class Player(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    first_login = models.DateTimeField(null=True, blank=True)  #аналитика первого входа
    last_login = models.DateTimeField(null=True, blank=True)
    login_count = models.PositiveIntegerField(default=0)
    daily_points = models.PositiveIntegerField(default=0)  #баллы за ежедневный вход
    total_points = models.PositiveIntegerField(default=0)  #общие баллы
    
    def __str__(self):
        return self.username
    
    def record_login(self):
        now = timezone.now()
        
        #отслеживание первого входа
        if not self.first_login:
            self.first_login = now
        
        self.last_login = now
        self.login_count += 1
        
        #начисление баллов за первый вход
        daily_bonus = 10
        self.daily_points += daily_bonus
        self.total_points += daily_bonus
        
        self.save()


class BoostType(models.Model):
    #бусты
    BOOST_TYPES = [
        ('speed', 'Speed Boost'),
        ('damage', 'Damage Boost'),
        ('health', 'Health Boost'),
        ('experience', 'Experience Boost'),
        ('coins', 'Coins Boost'),
    ]
    
    name = models.CharField(max_length=50, choices=BOOST_TYPES, unique=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=60)  #длительность в секундах
    multiplier = models.FloatField(default=1.0)  #множитель
    
    def __str__(self):
        return self.get_name_display()


class Boost(models.Model):
    #модель бустов
    BOOST_SOURCES = [
        ('level_completion', 'Level Completion'),
        ('manual', 'Manual Assignment'),
        ('daily_reward', 'Daily Reward'),
        ('purchase', 'Purchase'),
    ]
    
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='boosts')
    boost_type = models.ForeignKey(BoostType, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)  #количество бустов
    source = models.CharField(max_length=20, choices=BOOST_SOURCES)
    level_earned = models.PositiveIntegerField(null=True, blank=True)  #уровень, за который получен
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.player.username} - {self.boost_type.name} x{self.quantity}"
    
    def activate(self):
        #активатор буста
        if self.quantity > 0 and not self.is_active:
            self.is_active = True
            self.used_at = timezone.now()
            self.expires_at = timezone.now() + timezone.timedelta(
                minutes=self.boost_type.duration_minutes
            )
            self.quantity -= 1
            self.save()
            return True
        return False
    
    def is_expired(self):
        #проверка истечения времени буста
        if self.expires_at and timezone.now() > self.expires_at:
            self.is_active = False
            self.save()
            return True
        return False
    
    @classmethod
    def award_boost_for_level(cls, player, boost_type, level_number, quantity=1):
        #начисление буста за прохождение уровня
        boost = cls.objects.create(
            player=player,
            boost_type=boost_type,
            quantity=quantity,
            source='level_completion',
            level_earned=level_number
        )
        return boost
    
    @classmethod
    def award_boost_manually(cls, player, boost_type, quantity=1):
        #ручное начисление буста
        boost = cls.objects.create(
            player=player,
            boost_type=boost_type,
            quantity=quantity,
            source='manual'
        )
        return boost


class PlayerBoostHistory(models.Model):
    #история использования буста
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    boost_type = models.ForeignKey(BoostType, on_delete=models.CASCADE)
    activated_at = models.DateTimeField()
    expired_at = models.DateTimeField()
    level_used = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-activated_at']


#второе задание

class PlayerTask2(models.Model):
    player_id = models.CharField(max_length=100)
    
    def __str__(self):
        return self.player_id


class Level(models.Model):
    #уровень
    title = models.CharField(max_length=100)
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return self.title


class Award(models.Model):
    #награда
    title = models.CharField(max_length=100)
    
    def __str__(self):
        return self.title


class PlayerLevel(models.Model):
    #связь игрока и уровня
    player = models.ForeignKey(PlayerTask2, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    completed = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    score = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ['player', 'level']
        
    def __str__(self):
        return f"{self.player.player_id} - {self.level.title}"


class LevelAward(models.Model):
    #связь уровня и награды
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    award = models.ForeignKey(Award, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['level', 'award'] 
        
    def __str__(self):
        return f"{self.level.title} - {self.award.title}"


class PlayerAward(models.Model):
    #полученные награды
    player = models.ForeignKey(PlayerTask2, on_delete=models.CASCADE)
    award = models.ForeignKey(Award, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    received = models.DateField(auto_now_add=True)
    
    class Meta:
        unique_together = ['player', 'award', 'level']
        
    def __str__(self):
        return f"{self.player.player_id} получил {self.award.title} за {self.level.title}"


class GameService:
    #игровая логика
    
    @staticmethod
    @transaction.atomic
    def assign_award_for_level_completion(player_id, level_id):
        #награда за прохождение уровня
        try:
            player = PlayerTask2.objects.get(id=player_id)
            level = Level.objects.get(id=level_id)
            
            player_level, created = PlayerLevel.objects.get_or_create(
                player=player,
                level=level,
                defaults={'is_completed': True, 'completed': timezone.now().date()}
            )
            
            if not player_level.is_completed:
                player_level.is_completed = True
                player_level.completed = timezone.now().date()
                player_level.save()
                
            level_awards = LevelAward.objects.filter(level=level)
            
            awards_received = []
            for level_award in level_awards:
                player_award, award_created = PlayerAward.objects.get_or_create(
                    player=player,
                    award=level_award.award,
                    level=level
                )
                
                if award_created:
                    awards_received.append(level_award.award)
                    
            return {
                'success': True,
                'player': player.player_id,
                'level': level.title,
                'award': [award.title for award in awards_received]
            }
        
        except PlayerTask2.DoesNotExist:
            return {'success': False, 'error': 'Игрок не найден'}
        except Level.DoesNotExist:
            return {'success': False, 'error': 'Уровень не найден'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
    @staticmethod
    def export_player_level_data_to_csv():
        #csv выгрузка
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="player_level_data.csv"'
        
        #буферизация
        output = io.StringIO()
        writer = csv.writer(output)
        
        #заголовки
        writer.writerow([
            'Player ID',
            'Level Title',
            'Is Completed',
            'Received Award'
        ])
        
        batch_size = 1000
        offset = 0
        
        while True:
            #запросы батчами
            player_levels = PlayerLevel.objects.select_related(
                'player', 'level'
            ).prefetch_related(
                'player__playeraward_set__award'
            )[offset:offset + batch_size]
            
            if not player_levels:
                break
            
            #награды за текущий уровень
            for player_level in player_levels:
                player_awards = PlayerAward.objects.filter(
                    player=player_level.player,
                    level=player_level.level
                ).select_related('award')
                
                #строка для каждой награды, если есть
                if player_awards.exists():
                    for player_award in player_awards:
                        writer.writerow([
                            player_level.player.player_id,
                            player_level.level.title,
                            'Да' if player_level.is_completed else 'Нет',
                            player_award.award.title
                        ])
                else:
                    # строки без награды, если ее нет
                    writer.writerow([
                        player_level.player.player_id,
                        player_level.level.title,
                        'Да' if player_level.is_completed else 'Нет',
                        'Нет награды'
                    ])
            offset += batch_size
            
        #запись данных
        response.write(output.getvalue())
        output.close()
        
        return response