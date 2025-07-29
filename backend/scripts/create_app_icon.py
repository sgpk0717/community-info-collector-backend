#!/usr/bin/env python3
"""
트렌디한 커뮤니티 정보 수집기 앱 아이콘 생성 스크립트
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

def create_app_icon():
    # 기본 설정
    base_size = 512
    background_color = '#2c3e50'  # 다크 블루
    accent_color = '#3498db'      # 브라이트 블루
    secondary_color = '#e74c3c'   # 빨간색
    text_color = '#ffffff'        # 흰색
    
    # 이미지 생성
    img = Image.new('RGB', (base_size, base_size), background_color)
    draw = ImageDraw.Draw(img)
    
    # 그라데이션 효과를 위한 원형 배경
    center = base_size // 2
    gradient_radius = base_size // 3
    
    # 메인 원형 배경
    draw.ellipse([
        center - gradient_radius, 
        center - gradient_radius,
        center + gradient_radius, 
        center + gradient_radius
    ], fill=accent_color)
    
    # 검색 아이콘 (돋보기) 그리기
    search_radius = 60
    search_center_x = center - 30
    search_center_y = center - 30
    
    # 돋보기 원
    draw.ellipse([
        search_center_x - search_radius,
        search_center_y - search_radius,
        search_center_x + search_radius,
        search_center_y + search_radius
    ], outline=text_color, width=12)
    
    # 돋보기 손잡이
    handle_start_x = search_center_x + int(search_radius * 0.7)
    handle_start_y = search_center_y + int(search_radius * 0.7)
    handle_end_x = handle_start_x + 40
    handle_end_y = handle_start_y + 40
    
    draw.line([handle_start_x, handle_start_y, handle_end_x, handle_end_y], 
              fill=text_color, width=12)
    
    # 데이터 포인트들 (커뮤니티 정보를 상징)
    points = [
        (center + 80, center - 80),
        (center + 120, center - 40),
        (center + 100, center + 20),
        (center + 60, center + 80),
        (center - 60, center + 100),
        (center - 100, center + 60),
    ]
    
    # 포인트들을 선으로 연결
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=secondary_color, width=4)
    
    # 데이터 포인트 원들
    for point in points:
        draw.ellipse([point[0] - 8, point[1] - 8, point[0] + 8, point[1] + 8], 
                     fill=secondary_color)
    
    # 작은 아이콘들 (소셜 미디어 심볼)
    # Reddit 스타일 원
    reddit_x, reddit_y = center - 120, center + 40
    draw.ellipse([reddit_x - 15, reddit_y - 15, reddit_x + 15, reddit_y + 15], 
                 fill=secondary_color)
    
    # 트위터 스타일 점들
    twitter_points = [(center + 140, center + 60), (center + 150, center + 80), (center + 160, center + 100)]
    for point in twitter_points:
        draw.ellipse([point[0] - 6, point[1] - 6, point[0] + 6, point[1] + 6], 
                     fill=text_color)
    
    return img

def resize_for_android(base_image, target_size):
    """Android 다양한 해상도용 이미지 리사이즈"""
    return base_image.resize((target_size, target_size), Image.Resampling.LANCZOS)

def create_round_icon(square_icon):
    """라운드 아이콘 생성"""
    size = square_icon.size[0]
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([0, 0, size, size], fill=255)
    
    result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    result.paste(square_icon, (0, 0))
    result.putalpha(mask)
    
    return result

def main():
    # 기본 아이콘 생성
    print("🎨 트렌디한 앱 아이콘 생성 중...")
    base_icon = create_app_icon()
    
    # Android 해상도별 폴더 및 크기 정의
    android_sizes = {
        'mipmap-mdpi': 48,
        'mipmap-hdpi': 72,
        'mipmap-xhdpi': 96,
        'mipmap-xxhdpi': 144,
        'mipmap-xxxhdpi': 192
    }
    
    base_path = '/Users/seonggukpark/community-info-collector-v2.0/CommunityInfoCollectorNew/android/app/src/main/res'
    
    for folder, size in android_sizes.items():
        folder_path = os.path.join(base_path, folder)
        
        # 일반 아이콘
        square_icon = resize_for_android(base_icon, size)
        square_icon.save(os.path.join(folder_path, 'ic_launcher.png'))
        
        # 라운드 아이콘
        round_icon = create_round_icon(square_icon)
        round_icon.save(os.path.join(folder_path, 'ic_launcher_round.png'))
        
        print(f"✅ {folder} 아이콘 생성 완료 ({size}x{size})")
    
    print("🚀 모든 아이콘 생성 완료!")
    print("💡 아이콘 컨셉: 다크 블루 배경 + 돋보기 + 네트워크 연결 + 소셜 미디어 심볼")

if __name__ == "__main__":
    main()