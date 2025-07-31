# Bedrock Universal Model Caller

AWS Bedrock의 모든 사용 가능한 모델에 자동으로 API 호출을 수행하는 고급 도구입니다.

## 주요 기능

### 🚀 완전 자동화
- **모든 모델 자동 탐지**: 지정된 리전의 모든 Foundation Model 자동 스캔
- **스마트 필터링**: 호출 불가능한 모델 사전 제거 (`:28k`, `:200k`, `:mm` 등)
- **S3 버킷 자동 생성**: 계정 ID 기반 버킷 자동 생성 및 관리

### 🌐 Cross-Region 지원
- **리전별 최적화**: 
  - `ap-northeast-2` (서울): APAC inference profile 사용
  - `us-east-1` (버지니아): US inference profile 사용
  - 기타 리전: 로컬 모델 직접 호출
- **자동 라우팅**: Cross-region 필요 모델 자동 감지 및 처리

### 🎯 모델별 맞춤 호출
- **텍스트 생성**: Claude, Nova, Llama, Mistral, Jamba, DeepSeek 등
- **이미지 생성**: Titan Image Generator, Stable Diffusion, Nova Canvas
- **임베딩**: Titan Embed, Cohere Embed, Marengo Embed
- **비동기 처리**: TwelveLabs Marengo, Nova Reel (비디오 생성)
- **스트리밍**: Nova Sonic (음성, 현재 스킵)

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

```bash
python bedrock_token_sender.py
```

### 입력 정보
- **AWS Access Key ID**: IAM 사용자 액세스 키
- **AWS Secret Access Key**: IAM 사용자 시크릿 키
- **AWS Region**: 대상 리전 (예: `us-east-1`, `ap-northeast-2`)

## 지원 모델 현황

### ✅ 완전 지원 (동기 호출)
- **Amazon**: Titan Text/Image Generator, Nova Pro/Lite/Micro/Premier/Canvas
- **Anthropic**: Claude 3/3.5/4 시리즈 (Cross-region 포함)
- **Meta**: Llama 3/3.1/3.2/3.3/4 시리즈 (Cross-region 포함)
- **Mistral**: 7B/8x7B/Large/Small, Pixtral (Cross-region 포함)
- **AI21**: Jamba 시리즈
- **Cohere**: Command 시리즈, Embed 시리즈
- **DeepSeek**: R1 (Cross-region 포함)
- **Stability**: Stable Diffusion XL

### ⚡ 비동기 지원
- **TwelveLabs**: Marengo Embed 2.7 (S3 결과 저장)
- **Amazon**: Nova Reel (비디오 생성, S3 결과 저장)

### ⏭️ 스킵 처리
- **Nova Sonic**: 스트리밍 API 필요 (현재 미지원)
- **Claude Opus**: 접근 권한 제한
- **버전 충돌 모델**: `:28k`, `:200k`, `:mm`, 특정 `:0` 버전

## 실행 결과 예시

```
S3 버킷 생성: bedrock-output-123456789012-us-east-1

호출 가능한 모델 목록 (58개):
1. amazon.titan-tg1-large
2. amazon.nova-pro-v1:0
...

토큰 전송 시작...

✓ amazon.titan-tg1-large: 성공
✓ amazon.nova-pro-v1:0: 성공 (cross-region: us.amazon.nova-pro-v1:0)
✓ anthropic.claude-3-5-sonnet-20240620-v1:0: 성공
✓ meta.llama3-3-70b-instruct-v1:0: 성공 (cross-region: us.meta.llama3-3-70b-instruct-v1:0)
✓ twelvelabs.marengo-embed-2-7-v1:0: 성공 (비동기)
- amazon.nova-sonic-v1:0: 스트리밍 API 필요 (스킵)

완료: 52/58 모델 성공
```

## 기술적 특징

### 🔧 스마트 요청 형식
각 모델 패밀리별로 최적화된 JSON 페이로드 자동 생성:

```python
# Claude 시리즈
{
  "messages": [{"role": "user", "content": "Hello"}],
  "max_tokens": 10,
  "anthropic_version": "bedrock-2023-05-31"
}

# Nova Canvas (이미지 생성)
{
  "taskType": "TEXT_IMAGE",
  "textToImageParams": {"text": "Hello world"},
  "imageGenerationConfig": {"numberOfImages": 1, "height": 512, "width": 512}
}

# Llama 시리즈 (Cross-region)
{
  "messages": [{"role": "user", "content": "Hello"}],
  "max_tokens": 10,
  "temperature": 0.1
}
```

### 🌍 Cross-Region Inference Profile
자동으로 리전별 최적 경로 선택:
- 서울 → APAC 권역 (`apac.` 접두사)
- 버지니아 → US 권역 (`us.` 접두사)
- 추가 요금 없이 AWS 백본 네트워크 활용

### 📊 비동기 작업 모니터링
- 실시간 상태 폴링 (최대 60초)
- S3 결과 자동 확인
- 타임아웃 시 안전한 스킵 처리

## 요구사항

- Python 3.7+
- boto3 1.34.0+
- AWS 자격 증명 (Access Key/Secret Key)
- Bedrock 모델 접근 권한
- S3 버킷 생성 권한 (비동기 모델용)
