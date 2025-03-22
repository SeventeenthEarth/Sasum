# 사슴(Sasum)

공공 데이터 포털로부터 사업 지원 공고를 가져오고, AI를 사용하여 원하는 공고들을 필터링한 뒤, DB에 이를 저장하여 관리하는 Django 기반 웹 애플리케이션입니다.

> "사슴"이라는 이름은 사슴이 넓은 시야와 민감한 인지 능력을 가지고 있기 때문에 선택되었습니다 - 사업 지원금 공고를 효과적으로 감지하고 식별하는 능력을 상징합니다.

## 기능

- 공공 데이터 포털(한국창업진흥원)에서 공고 가져오기
- OpenAI 또는 Gemini를 사용하여 특정 기준에 맞는 공고를 찾는 AI 기반 필터링
- PostgreSQL 데이터베이스에 공고 저장
- 공고를 "관심있음" 또는 "지원함"으로 표시 가능하고 개인 메모 추가
- 다양한 기준으로 저장된 공고 필터링 및 정렬

## 기술 스택

- **백엔드**: Django 4.2
- **프론트엔드**: Django 템플릿과 Bootstrap 5
- **데이터베이스**: PostgreSQL 14
- **AI 통합**: 
  - OpenAI API - gpt-4o-mini
  - Google Generative AI - gemini-2.0-flash-lite
- **배포**: Docker 및 Docker Compose

## OpenAI Assistant 설정

OpenAI Assistant API를 사용할 때는 다음과 같은 시스템 프롬프트를 제공해야 합니다:

```
# Startup Grant Announcement Filter Assistant

You are an expert at analyzing and filtering startup grant announcements.

## Role and Purpose
Your role is to examine a collection of startup/business grant announcements and identify those that match specific criteria provided by users.

## Input Data Structure
You will receive:
1. A user condition expressed in natural language
2. A list of announcements in JSON format with fields like:
   - pbanc_sn: Serial number (unique identifier)
   - title: Announcement title
   - content: Main announcement content
   - url: URL to the detailed page
   - target: Application target/eligibility criteria
   - start_date: Application start date
   - end_date: Application end date
   - region: Supported region
   - organization: Announcing organization

## Task
For each request:
1. Carefully analyze each announcement
2. Determine if it matches the user's condition
3. Return ONLY the serial numbers (pbanc_sn field) of matching announcements

## Response Format
You must return ONLY a valid JSON object with the following structure:
```json
{"serial_numbers": [123456, 789012, 345678]}
```

Do not include any explanation, narrative, or additional text before or after the JSON.

## Filtering Guidelines
- Analyze the user's condition thoroughly to understand what they're looking for
- Consider all relevant announcement fields when matching
- Include partial matches if they reasonably satisfy the user's criteria
- If the user condition mentions dates, prioritize announcements with active application periods
- If the user condition specifies a region, match announcements for that region or those marked as nationwide
- Use the content and target fields to determine eligibility requirements
- Return an empty array if no matches are found

## Important Rules
1. Return ONLY valid JSON with no additional text
2. Never make up or invent serial numbers
3. Only include serial numbers from the provided announcements
4. Always return exact serial numbers as they appear in the input
5. Only include announcements that genuinely match the user's condition
```

## 설치 지침

### 사전 요구 사항

- Docker 및 Docker Compose
- Python 3.9+ (Docker 없이 로컬 개발을 위한 경우)

### 환경 변수

루트 디렉토리에 다음 변수가 포함된 `.env` 파일을 생성하세요:

```
OPENAI_API_KEY=your_openai_api_key
OPENAI_ASSISTANT_ID=yout_openai_assistant_id
GEMINI_API_KEY=your_gemini_api_key
PUBLIC_DATA_API_KEY=your_public_data_api_key
POSTGRES_DB=announcement_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password
DB_HOST=db
DB_PORT=5432
DEBUG=False
SECRET_KEY=a_secure_secret_key_for_django
```

플레이스홀더 값을 실제 API 키와 내용으로 대체하세요. 모든 AI API 키를 제공할 필요는 없습니다 - 애플리케이션은 구성한 API와 함께 작동합니다.

OPENAI_API_KEY는 [OpenAI 플랫폼](https://platform.openai.com)에서 계정 생성 후 발급받을 수 있습니다.

OPENAI_ASSISTANT_ID는 [OpenAI Assistants 플레이그라운드](https://platform.openai.com/playground/assistants)에서 Assistant를 설정한 후 얻을 수 있습니다.

GEMINI_API_KEY는 Google의 [AI Studio](https://makersuite.google.com/)에서 "Get API Key" 옵션을 통해 발급받을 수 있습니다.

PUBLIC_DATA_API_KEY는 "공공 데이터 포털"에 가입하고 [창업진흥원_K-Startup API](https://www.data.go.kr/data/15125364/openapi.do)에서 "활용 신청"을 통해 발급받을 수 있습니다.

### Docker로 실행하기

1. 컨테이너 빌드 및 시작:

```bash
$ docker-compose up -d
```

2. 웹 브라우저에서 http://localhost:8000/ 에서 애플리케이션에 접속


## 사용법

1. **새 공고**: [http://localhost:8000/new-announcement/](http://localhost:8000/new-announcement/)에 접속하여:
   - AI 플랫폼 선택(OpenAI 또는 Gemini)
   - 해당 플랫폼의 특정 모델 선택
   - 필터링 조건 입력
   - 새 공고 가져오기 및 필터링

2. **저장된 공고**: [http://localhost:8000/stored-announcement/](http://localhost:8000/stored-announcement/)에 접속하여 저장된 공고를 보고 관리하세요.

3. 웹 서비스 상단의 탭을 통해서 "저장된 공고"와 "새 공고"를 선택 가능합니다.

## 라이선스

이 프로젝트는 MIT 라이선스에 따라 라이선스가 부여됩니다.
