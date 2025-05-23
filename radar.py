import RPi.GPIO as GPIO
import time
import pygame
import math
import sys

# Configuración de colores
class colors:
    black = (0, 0, 0)
    green = (0, 255, 0)
    white = (255, 255, 255)
    red = (255, 50, 50)
    dark_green = (0, 100, 0)
    blue = (100, 100, 255)
    target_colors = [
        (255, 0, 0),    # Rojo intenso
        (255, 80, 80),  # Rojo claro
        (200, 60, 60)   # Rojo oscuro
    ]

# Inicialización de GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Configuración del servo
SERVO_PIN = 18
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz (frecuencia estándar para servos)
pwm.start(0)

# Configuración del HC-SR04
TRIG = 23
ECHO = 24
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Configuración de Pygame
pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Radar Ultrasónico (0-50cm) - Funcionamiento Corregido")
FONT = pygame.font.SysFont('Arial', 18)
LARGE_FONT = pygame.font.SysFont('Arial', 24, bold=True)

# Parámetros del radar
MAX_DISTANCE = 50  # 50 cm máximo
radar_center = (WIDTH//2, HEIGHT-50)
radar_radius = min(WIDTH, HEIGHT) - 100
scan_speed = 2  # Grados por frame (aumentado para mayor velocidad)
targets = []

class Target:
    def __init__(self, angle, distance):
        self.angle = angle
        self.distance = distance
        self.time = time.time()
        self.color_index = 0

def set_servo_angle(angle):
    # Asegurar que el ángulo esté dentro del rango válido
    angle = max(0, min(180, angle))
    # Calcular ciclo de trabajo (2.5% a 12.5% para 0° a 180°)
    duty_cycle = 2.5 + (angle / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.02)  # Pequeña pausa para que el servo responda

def get_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.01)
    
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)
    
    pulse_start = time.time()
    pulse_end = pulse_start
    
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if pulse_start - pulse_end > 0.1:
            return MAX_DISTANCE
    
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        if pulse_end - pulse_start > 0.1:
            return MAX_DISTANCE
    
    pulse_duration = pulse_end - pulse_start
    distance = (pulse_duration * 34300) / 2  # Velocidad del sonido en cm/s
    return max(0, min(round(distance, 1), MAX_DISTANCE))

def draw_radar(angle, distance):
    screen.fill(colors.black)
    
    # Dibujar semicírculo del radar
    pygame.draw.arc(screen, colors.dark_green, 
                   (radar_center[0]-radar_radius, radar_center[1]-radar_radius, 
                    radar_radius*2, radar_radius*2),
                   math.radians(0), math.radians(180), 2)
    
    # Líneas de distancia (cada 10cm)
    for r in range(radar_radius, 0, -radar_radius//5):
        pygame.draw.arc(screen, colors.green, 
                       (radar_center[0]-r, radar_center[1]-r, r*2, r*2),
                       math.radians(0), math.radians(180), 1)
        
        # Etiquetas de distancia
        dist = int((r/radar_radius)*MAX_DISTANCE)
        if dist > 0:
            dist_text = FONT.render(f"{dist}cm", True, colors.green)
            screen.blit(dist_text, (radar_center[0] - r - 20, radar_center[1] - 15))
            screen.blit(dist_text, (radar_center[0] + r - 20, radar_center[1] - 15))
    
    # Líneas de ángulo (cada 30°)
    for deg in range(0, 181, 30):
        rad = math.radians(deg)
        end_x = radar_center[0] + radar_radius * math.cos(rad)
        end_y = radar_center[1] - radar_radius * math.sin(rad)
        pygame.draw.line(screen, colors.green, radar_center, (end_x, end_y), 1)
        
        angle_text = FONT.render(f"{deg}°", True, colors.green)
        if deg == 0:
            screen.blit(angle_text, (end_x + 10, end_y - 10))
        elif deg == 180:
            screen.blit(angle_text, (end_x - 30, end_y - 10))
        else:
            screen.blit(angle_text, (end_x - 15, end_y - 15))
    
    # Línea de barrido actual
    rad_angle = math.radians(angle)
    end_x = radar_center[0] + radar_radius * math.cos(rad_angle)
    end_y = radar_center[1] - radar_radius * math.sin(rad_angle)
    pygame.draw.line(screen, colors.blue, radar_center, (end_x, end_y), 2)
    
    # Panel de información
    pygame.draw.rect(screen, colors.green, (10, 10, 250, 80), 1)
    angle_text = LARGE_FONT.render(f"Ángulo: {angle}°", True, colors.white)
    dist_text = LARGE_FONT.render(f"Distancia: {distance if distance < MAX_DISTANCE else '---'} cm", 
                                True, colors.white)
    screen.blit(angle_text, (20, 20))
    screen.blit(dist_text, (20, 50))
    
    # Dibujar objetivos detectados
    for target in targets[:]:
        # Calcular posición
        target_rad = math.radians(target.angle)
        target_dist = (target.distance/MAX_DISTANCE) * radar_radius
        target_x = radar_center[0] + target_dist * math.cos(target_rad)
        target_y = radar_center[1] - target_dist * math.sin(target_rad)
        
        # Dibujar punto
        pygame.draw.circle(screen, colors.target_colors[target.color_index], 
                         (int(target_x), int(target_y)), 6)
        
        # Mostrar distancia
        dist_text = FONT.render(f"{target.distance}cm", True, colors.white)
        text_rect = dist_text.get_rect(center=(target_x, target_y - 15))
        screen.blit(dist_text, text_rect)
        
        # Actualizar desvanecimiento
        target.color_index = min(target.color_index + 1, len(colors.target_colors)-1)
        
        # Eliminar objetivos antiguos
        if time.time() - target.time > 1.5:
            targets.remove(target)
    
    pygame.display.flip()

def main():
    try:
        clock = pygame.time.Clock()
        running = True
        current_angle = 0
        direction = 1  # 1 para derecha, -1 para izquierda
        
        # Secuencia de inicialización del servo
        print("Inicializando servo...")
        for angle in [90, 0, 90, 180, 90]:
            set_servo_angle(angle)
            time.sleep(0.3)
        
        print("Iniciando radar...")
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            # Actualizar ángulo
            current_angle += scan_speed * direction
            
            # Cambiar dirección al llegar a los límites
            if current_angle >= 180:
                current_angle = 180
                direction = -1
            elif current_angle <= 0:
                current_angle = 0
                direction = 1
            
            # Mover servo y medir distancia
            set_servo_angle(current_angle)
            distance = get_distance()
            
            if distance < MAX_DISTANCE:
                targets.append(Target(current_angle, distance))
            
            draw_radar(current_angle, distance)
            clock.tick(60)  # 60 FPS

    except KeyboardInterrupt:
        pass
    finally:
        print("\nDeteniendo radar...")
        pwm.stop()
        GPIO.cleanup()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    main()