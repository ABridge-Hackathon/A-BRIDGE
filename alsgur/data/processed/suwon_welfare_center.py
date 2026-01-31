import pandas as pd
import os
import json
from haversine import haversine

# ==========================================
# 1. 설정 및 데이터 로드 (초기화)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 파일 설정 (수원, 강릉, 파주)
CSV_CONFIGS = [
    {
        "region": "수원시",
        "path": "data/raw/경기도_수원시_노인복지시설현황_20250411.csv",
        "encoding": "cp949" 
    },
    {
        "region": "강릉시",
        "path": "data/raw/강원특별자치도 강릉시_노인복지시설현황_20250305.csv",
        "encoding": "cp949"
    },
    {
        "region": "파주시",
        "path": "data/raw/경기도 파주시_노인복지시설현황_20251202.csv",
        "encoding": "utf-8"
    }
]

def _standardize_columns(df):
    """컬럼명 표준화 및 전처리 (내부 함수)"""
    rename_map = {}
    
    # 시설구분 매핑
    if '시설종류' in df.columns: rename_map['시설종류'] = '시설구분'       
    elif '제공서비스' in df.columns: rename_map['제공서비스'] = '시설구분'   
    elif '시설유형' in df.columns: rename_map['시설유형'] = '시설구분'
    
    # 주소/좌표 매핑
    if '소재지도로명주소' in df.columns: rename_map['소재지도로명주소'] = '주소'
    elif '도로명주소' in df.columns: rename_map['도로명주소'] = '주소'
    if 'WGS84위도' in df.columns: rename_map['WGS84위도'] = '위도'
    if 'WGS84경도' in df.columns: rename_map['WGS84경도'] = '경도'

    if rename_map:
        df = df.rename(columns=rename_map)
        
    # 필수 컬럼 결측치 처리
    if '시설구분' not in df.columns:
        df['시설구분'] = df['시설명'] # 시설구분 없으면 이름으로 대체
        
    return df

def load_data():
    """데이터 로드 및 통합"""
    merged_list = []
    print("🚀 [System] 데이터 로딩 중...")
    
    for config in CSV_CONFIGS:
        full_path = os.path.normpath(os.path.join(BASE_DIR, "../../", config['path']))
        try:
            df = pd.read_csv(full_path, encoding=config.get('encoding', 'cp949'))
            df = _standardize_columns(df)
            
            # 좌표 유효성 검사
            if '위도' in df.columns and '경도' in df.columns:
                df['위도'] = pd.to_numeric(df['위도'], errors='coerce')
                df['경도'] = pd.to_numeric(df['경도'], errors='coerce')
                df = df.dropna(subset=['위도', '경도'])
                
                df['region_source'] = config['region']
                merged_list.append(df)
        except Exception as e:
            print(f"⚠️ {config['region']} 로드 실패: {e}")

    if merged_list:
        final_df = pd.concat(merged_list, ignore_index=True)
        final_df = final_df.fillna('') # JSON 변환 시 NaN 에러 방지
        print(f"✅ [System] 데이터 준비 완료 (총 {len(final_df)}개 시설)")
        return final_df
    else:
        return pd.DataFrame() # 빈 프레임 반환

# 전역 변수로 데이터 로드 (서버 실행 시 1회만 로드됨)
GLOBAL_DF = load_data()


# ==========================================
# 2. AI 추천 로직 (외부 호출용 함수)
# ==========================================
def get_ai_recommendations(user_lat, user_lon, user_interest='건강케어', max_dist_km=50, limit=5):
    """
    백엔드에서 호출하는 메인 함수
    :param user_lat: 사용자 위도
    :param user_lon: 사용자 경도
    :param user_interest: 관심사 ('건강케어', '생활도움', '주거지원')
    :return: JSON 호환 Dictionary
    """
    if GLOBAL_DF.empty:
        return {"status": "error", "message": "데이터가 로드되지 않았습니다."}
    
    user_pos = (user_lat, user_lon)
    
    # 복사본 생성 (원본 보존)
    df = GLOBAL_DF.copy()
    
    # 1. 거리 계산
    df['dist_km'] = df.apply(lambda x: haversine(user_pos, (x['위도'], x['경도']), unit='km'), axis=1)
    
    # 2. 관심사 필터링 로직
    interest_map = {
        '건강케어': ['의료', '요양', '병원', '치매', '간호'],
        '생활도움': ['재가', '주간보호', '방문', '돌봄', '복지관'],
        '주거지원': ['주거', '양로', '공동생활', '입소']
    }
    keywords = interest_map.get(user_interest, [])
    
    def calculate_score(row):
        score = 10 / (row['dist_km'] + 0.5) # 거리 점수
        
        # 키워드 가산점
        content = (str(row['시설구분']) + str(row['시설명'])).replace("nan", "")
        for k in keywords:
            if k in content:
                score += 20
                break
        return score

    df['ai_score'] = df.apply(calculate_score, axis=1)
    
    # 3. 결과 정렬 및 포맷팅
    results = df[df['dist_km'] <= max_dist_km] \
                .sort_values(by='ai_score', ascending=False) \
                .head(limit)
    
    if results.empty:
        return {"status": "empty", "message": "근처에 적합한 시설이 없습니다."}
    
    data_list = []
    for _, row in results.iterrows():
        data_list.append({
            "name": row['시설명'],
            "category": row['시설구분'],
            "region": row['region_source'],
            "address": row['주소'],
            "latitude": row['위도'],
            "longitude": row['경도'],
            "distance_km": round(row['dist_km'], 1),
            "match_score": round(row['ai_score'], 1),
            "phone": row.get('전화번호', '') # 전화번호 있으면 추가
        })
        
    return {
        "status": "success", 
        "request_interest": user_interest,
        "count": len(data_list),
        "data": data_list
    }

# ==========================================
# 3. 실행부 (이 파일 직접 실행 시 JSON 생성)
# ==========================================
if __name__ == "__main__":
    print("\n--- 💾 백엔드 전달용 JSON 파일 생성 중... ---")
    
    # 시나리오별 샘플 데이터 생성
    sample_output = {
        "description": "노인 복지 시설 AI 추천 결과 샘플",
        "scenarios": {
            "case_suwon_health": get_ai_recommendations(37.266, 127.000, '건강케어'),
            "case_gangneung_life": get_ai_recommendations(37.751, 128.876, '생활도움'),
            "case_paju_house": get_ai_recommendations(37.760, 126.779, '주거지원')
        }
    }
    
    # JSON 파일로 저장
    with open("recommendation_results.json", "w", encoding='utf-8') as f:
        json.dump(sample_output, f, ensure_ascii=False, indent=4)
        
    print(f"✅ 저장 완료: {os.path.abspath('recommendation_results.json')}")
    print("👉 이 파일과 파이썬 스크립트를 백엔드 개발자에게 전달하세요.")