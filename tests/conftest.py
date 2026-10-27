"""테스트 공통 설정.

앱 import 전에 더미 환경변수를 주입해, 실제 Supabase/JWT 자격증명 없이도
테스트가 돌아가도록 한다. (`create_client` 는 구성 시점에 네트워크 호출을
하지 않으므로 더미 값으로 충분하다.)
"""

import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("JWT_SECRET", "test-secret-key-at-least-32-bytes-long!!")
