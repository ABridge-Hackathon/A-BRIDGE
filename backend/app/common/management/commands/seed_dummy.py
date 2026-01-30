# app/common/management/commands/seed_dummy.py
from __future__ import annotations

import uuid
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from app.friends.models import Friend
from app.care.models import CareRelation

from app.calls.models import CallLog, CallAnalysis
from app.transcripts.models import Transcript


def _uuid_for_field(model, field_name: str):
    """
    CallLog.call_id가 UUIDField인지 CharField인지 몰라도 안전하게 넣기 위한 helper.
    - UUIDField  -> uuid.UUID
    - CharField  -> str(uuid)
    """
    f = model._meta.get_field(field_name)
    if f.__class__.__name__ == "UUIDField":
        return uuid.uuid4()
    return str(uuid.uuid4())


def _dt(s: str) -> date:
    y, m, d = map(int, s.split("-"))
    return date(y, m, d)


class Command(BaseCommand):
    help = "Seed dummy data for ASCII backend (adminpanel demo)"

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        now = timezone.now()

        # ---------------------------------------------------------------------
        # 0) 유저 upsert helper
        # ---------------------------------------------------------------------
        def upsert_user(phone_number: str, defaults: dict, password: str = "test1234!"):
            user, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={
                    **defaults,
                    "phone_number": phone_number,
                    "created_at": defaults.get("created_at", now),
                },
            )

            # 데모용: 기존 유저도 defaults로 덮어씌움
            changed = False
            for k, v in defaults.items():
                if hasattr(user, k) and getattr(user, k) != v:
                    setattr(user, k, v)
                    changed = True

            if created:
                user.set_password(password)
                changed = True

            if changed:
                user.save()
            return user, created

        # ---------------------------------------------------------------------
        # 1) "유저(어르신)" 10명 생성
        #    - adminpanel 1번 페이지: 복지사가 전체 유저 조회
        #    - 송민혁 = 시연 주인공(대화/통화 탭에서 볼 유저)
        # ---------------------------------------------------------------------
        users_data = [
            dict(
                phone_number="01040823455",
                name="송민혁",
                gender="M",
                birth_year=1954,
                birth_date=_dt("1954-05-15"),
                address="전라북도 익산시",
                profile_image_url="/static/images/profiles/senior_songminhyeok.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01012345678",
                name="김철수",
                gender="M",
                birth_year=1944,
                birth_date=_dt("1944-05-15"),
                address="서울시 관악구 봉천동",
                profile_image_url="/static/images/profiles/senior_kimchulsu.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01022223333",
                name="이영희",
                gender="F",
                birth_year=1948,
                birth_date=_dt("1948-09-03"),
                address="서울시 강서구 화곡동",
                profile_image_url="/static/images/profiles/senior_leeyounghee.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01044445555",
                name="박민수",
                gender="M",
                birth_year=1951,
                birth_date=_dt("1951-01-22"),
                address="인천시 부평구 부평동",
                profile_image_url="/static/images/profiles/senior_parkminsu.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01066667777",
                name="최자두",
                gender="F",
                birth_year=1947,
                birth_date=_dt("1947-12-11"),
                address="대전시 서구 둔산동",
                profile_image_url="/static/images/profiles/senior_choijadu.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01088889999",
                name="정순복",
                gender="F",
                birth_year=1950,
                birth_date=_dt("1950-06-05"),
                address="부산시 해운대구 우동",
                profile_image_url="/static/images/profiles/senior_jeongsunbok.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01033334444",
                name="한경자",
                gender="F",
                birth_year=1952,
                birth_date=_dt("1952-03-10"),
                address="경기도 수원시 영통구",
                profile_image_url="/static/images/profiles/senior_hankyeongja.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01055556666",
                name="오정식",
                gender="M",
                birth_year=1946,
                birth_date=_dt("1946-08-29"),
                address="서울시 은평구 불광동",
                profile_image_url="/static/images/profiles/senior_ohjeongsik.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077778888",
                name="윤미자",
                gender="F",
                birth_year=1953,
                birth_date=_dt("1953-11-02"),
                address="광주시 북구 일곡동",
                profile_image_url="/static/images/profiles/senior_yoonmija.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01099990000",
                name="서동현",
                gender="M",
                birth_year=1949,
                birth_date=_dt("1949-04-17"),
                address="대구시 수성구 범어동",
                profile_image_url="/static/images/profiles/senior_seodonghyeon.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
        ]

        user_objs = []
        user_created = 0
        for u in users_data:
            obj, created = upsert_user(u["phone_number"], u)
            user_objs.append(obj)
            if created:
                user_created += 1

        # 시연 주인공
        demo_user = User.objects.get(phone_number="01040823455")

        self.stdout.write(
            self.style.SUCCESS(f"✅ users(10) upserted (created={user_created})")
        )

        # ---------------------------------------------------------------------
        # 2) "친구(통화 상대)" 15명 생성
        #    - 전부 demo_user(송민혁)의 친구가 됨
        # ---------------------------------------------------------------------
        friends_data = [
            dict(
                phone_number="01077770001",
                name="박사기",
                gender="M",
                birth_year=1980,
                birth_date=_dt("1980-01-01"),
                address="불명",
                profile_image_url="/static/images/profiles/peer_unknown_01.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=False,
            ),
            dict(
                phone_number="01077770002",
                name="최순자",
                gender="F",
                birth_year=1950,
                birth_date=_dt("1950-11-20"),
                address="부산시 영도구 동삼동",
                profile_image_url="/static/images/profiles/peer_choisoonja.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770003",
                name="이장수",
                gender="M",
                birth_year=1944,
                birth_date=_dt("1944-02-10"),
                address="경기도 수원시 팔달구",
                profile_image_url="/static/images/profiles/peer_leejansu.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770004",
                name="김유섭",
                gender="M",
                birth_year=1965,
                birth_date=_dt("1965-04-18"),
                address="광주시 북구",
                profile_image_url="/static/images/profiles/peer_kimyuseob.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770005",
                name="박한길",
                gender="M",
                birth_year=1948,
                birth_date=_dt("1948-03-15"),
                address="서울시 종로구 혜화동",
                profile_image_url="/static/images/profiles/peer_parkhangil.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            # --- 추가 10명 ---
            dict(
                phone_number="01077770006",
                name="김영희",
                gender="F",
                birth_year=1951,
                birth_date=_dt("1951-07-07"),
                address="서울시 관악구 신림동",
                profile_image_url="/static/images/profiles/senior_choijadu.jpgg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770007",
                name="정태수",
                gender="M",
                birth_year=1950,
                birth_date=_dt("1950-09-09"),
                address="서울시 노원구",
                profile_image_url="/static/images/profiles/senior_hankyeongja.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770008",
                name="한수진",
                gender="F",
                birth_year=1955,
                birth_date=_dt("1955-02-01"),
                address="경기도 성남시",
                profile_image_url="/static/images/profiles/senior_jeongsunbok.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770009",
                name="최남식",
                gender="M",
                birth_year=1947,
                birth_date=_dt("1947-06-21"),
                address="충청북도 청주시",
                profile_image_url="/static/images/profiles/senior_kimchulsu.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770010",
                name="오말순",
                gender="F",
                birth_year=1949,
                birth_date=_dt("1949-12-30"),
                address="강원도 춘천시",
                profile_image_url="/static/images/profiles/senior_leeyounghee.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770011",
                name="박정호",
                gender="M",
                birth_year=1952,
                birth_date=_dt("1952-04-04"),
                address="전라남도 여수시",
                profile_image_url="/static/images/profiles/senior_ohjeongsik.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770012",
                name="이미숙",
                gender="F",
                birth_year=1956,
                birth_date=_dt("1956-10-10"),
                address="경상북도 포항시",
                profile_image_url="/static/images/profiles/senior_parkminsu.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770013",
                name="권영철",
                gender="M",
                birth_year=1945,
                birth_date=_dt("1945-03-03"),
                address="울산시 남구",
                profile_image_url="/static/images/profiles/senior_seodonghyeon.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770014",
                name="서정자",
                gender="F",
                birth_year=1954,
                birth_date=_dt("1954-08-08"),
                address="서울시 동작구",
                profile_image_url="/static/images/profiles/senior_yoonmija.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077770015",
                name="조경수",
                gender="M",
                birth_year=1948,
                birth_date=_dt("1948-01-19"),
                address="경기도 고양시",
                profile_image_url="/static/images/profiles/peer_leejansu.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
        ]

        friend_objs = []
        friends_created = 0
        for f in friends_data:
            obj, created = upsert_user(f["phone_number"], f)
            friend_objs.append(obj)
            if created:
                friends_created += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ friends(15) upserted (created={friends_created})")
        )

        # ---------------------------------------------------------------------
        # 3) 복지사 1명 생성 (모든 유저를 볼 수 있음)
        # ---------------------------------------------------------------------
        worker_defaults = dict(
            phone_number="01099998888",
            name="김복지",
            gender="F",
            birth_year=1995,
            birth_date=_dt("1995-02-14"),
            address="서울시 구로구",
            profile_image_url="/static/images/profiles/worker_kimbokji.jpg",
            is_welfare_worker=True,
            is_active=True,
            is_phone_verified=True,
            # /admin 로그인도 필요하면 켜기
            is_staff=True,
            is_superuser=False,
        )
        worker, worker_created = upsert_user(
            worker_defaults["phone_number"], worker_defaults, password="test1234!"
        )
        self.stdout.write(
            self.style.SUCCESS(f"✅ welfare worker upserted (created={worker_created})")
        )

        # ---------------------------------------------------------------------
        # 4) CareRelation: 복지사 1명이 유저 10명 전부 관리
        # ---------------------------------------------------------------------
        cr_created = 0
        for u in user_objs:
            _, created = CareRelation.objects.get_or_create(
                welfare_worker=worker, senior=u
            )
            if created:
                cr_created += 1
        self.stdout.write(
            self.style.SUCCESS(f"✅ care_relations (10) done (created={cr_created})")
        )

        # ---------------------------------------------------------------------
        # 5) Friend: 유저(송민혁)의 친구 15명 연결
        # ---------------------------------------------------------------------
        fr_created = 0
        for f in friend_objs:
            _, created = Friend.objects.get_or_create(
                user=demo_user,
                friend_user=f,
                defaults={"created_at": now},
            )
            if created:
                fr_created += 1
        self.stdout.write(
            self.style.SUCCESS(f"✅ demo_user friends (15) done (created={fr_created})")
        )

        # ---------------------------------------------------------------------
        # 6) 통화/대화 기록 10개: "송민혁 ↔ 친구" 대화로 생성
        #    - 내용 템플릿(기존 유지)
        #    - session_id: sess-demo-001 ~ 010
        # ---------------------------------------------------------------------
        call_templates = [
            # (status, category, keywords, summary, peer_index, safe)
            (
                "DANGER",
                "기관사칭",
                ["검찰", "수사", "계좌이체", "구속"],
                "기관 사칭 및 금전 요구 패턴 감지",
                0,
                False,
            ),
            (
                "SAFE",
                "일상대화",
                ["경로당", "식사", "날씨"],
                "일상적인 안부 대화",
                1,
                True,
            ),
            (
                "WARNING",
                "언쟁",
                ["오해", "뒷담화", "말다툼"],
                "감정이 격해진 말다툼",
                3,
                False,
            ),
            ("DANGER", "욕설", ["폭언", "모욕"], "지속적인 폭언 감지", 3, False),
            ("WARNING", "우울", ["우울", "무기력"], "우울감 표현 빈도 증가", 4, False),
            ("SAFE", "건강", ["병원", "무릎", "주사"], "건강 관련 일상 대화", 2, True),
            (
                "WARNING",
                "로맨스",
                ["돈", "급해", "수술비"],
                "금전 요구가 동반된 관계 유도",
                0,
                False,
            ),
            ("SAFE", "취미", ["노래교실", "꽃놀이"], "긍정적인 감정 대화", 1, True),
            (
                "DANGER",
                "금융유도",
                ["대출", "인증번호", "비밀번호"],
                "금융정보/인증 요청 패턴 감지",
                0,
                False,
            ),
            ("SAFE", "가족", ["손주", "자랑", "용돈"], "가족 관련 일상 대화", 1, True),
        ]

        def make_dialogue_lines(senior_name: str, peer_name: str, theme: str) -> str:
            # 12줄 이상 (이름: 대화)
            if theme == "기관사칭":
                lines = [
                    f"{peer_name}: 어르신, 서울중앙지검입니다. 통장이 범죄에 연루되었어요.",
                    f"{senior_name}: 예? 제가요? 무슨 일이죠?",
                    f"{peer_name}: 지금 바로 조사해야 합니다. 통장 내역 확인하셔야 해요.",
                    f"{senior_name}: 저는 그런 거 한 적이 없는데요…",
                    f"{peer_name}: 일단 안전조치로 계좌를 분리해야 합니다.",
                    f"{peer_name}: 제가 알려드리는 계좌로 임시 이체만 하시면 됩니다.",
                    f"{senior_name}: 이체를 해야 하나요? 겁이 나네요.",
                    f"{peer_name}: 안 하시면 구속수사 들어갈 수 있습니다. 빨리 하세요.",
                    f"{senior_name}: 가족에게 물어봐도 될까요?",
                    f"{peer_name}: 지금은 외부에 말하면 안 됩니다. 바로 진행하세요.",
                    f"{senior_name}: 알겠습니다… 계좌를 불러주세요.",
                    f"{peer_name}: 네, 지금 말씀드리겠습니다.",
                ]
            elif theme == "금융유도":
                lines = [
                    f"{peer_name}: 어르신, 고객님 명의로 대출 신청이 들어왔습니다.",
                    f"{senior_name}: 대출이요? 저는 신청한 적이 없어요.",
                    f"{peer_name}: 본인 확인을 위해 인증번호가 필요합니다.",
                    f"{senior_name}: 문자로 온 건가요?",
                    f"{peer_name}: 네, 지금 오는 6자리 번호를 말씀해 주세요.",
                    f"{senior_name}: 이런 건 알려주면 안 된다고 들었는데…",
                    f"{peer_name}: 거절하면 피해가 커집니다. 바로 막아야 합니다.",
                    f"{senior_name}: 그래도 불안해서요.",
                    f"{peer_name}: 본인 보호를 위한 절차입니다. 신속히 진행해야 합니다.",
                    f"{senior_name}: 가족에게 확인하고 다시 연락드릴게요.",
                    f"{peer_name}: 지금 끊으면 취소가 안 됩니다. 번호만 말씀하세요.",
                    f"{senior_name}: 죄송하지만 못 드리겠습니다.",
                ]
            elif theme == "로맨스":
                lines = [
                    f"{peer_name}: 오빠~ 나 지금 너무 급한데 잠깐만 도와줄 수 있어?",
                    f"{senior_name}: 무슨 일인데 그래?",
                    f"{peer_name}: 수술비가 모자라서… 50만 원만 빌려줘.",
                    f"{senior_name}: 얼굴도 못 봤는데 돈 이야기는 좀…",
                    f"{peer_name}: 나 믿지? 내가 얼마나 오빠 생각하는데.",
                    f"{senior_name}: 어디 병원이야? 영수증 같은 건 있어?",
                    f"{peer_name}: 지금 너무 급해서 그런 거 못 보내. 빨리 보내줘.",
                    f"{senior_name}: 급할수록 확인이 필요해.",
                    f"{peer_name}: 의심하면 나 상처 받아… 나 정말 아파.",
                    f"{senior_name}: 미안하지만 확인되기 전엔 어려워.",
                    f"{peer_name}: 그럼 나 혼자 어떻게 해…",
                    f"{senior_name}: 가까운 사람에게 먼저 연락해 봐.",
                ]
            elif theme == "욕설":
                lines = [
                    f"{peer_name}: 야, 말귀를 못 알아듣냐?",
                    f"{senior_name}: 왜 그러세요, 말씀을 곱게 하셔야죠.",
                    f"{peer_name}: 곱게? 지금 장난하냐?",
                    f"{senior_name}: 저는 모르는 번호라 조심스러워서요.",
                    f"{peer_name}: 늙어서 답답하네.",
                    f"{senior_name}: 그만 말씀하세요.",
                    f"{peer_name}: 당장 끊어. 시간 낭비야.",
                    f"{senior_name}: 이런 식이면 통화 못 합니다.",
                    f"{peer_name}: 그러든가 말든가.",
                    f"{senior_name}: 네, 끊겠습니다.",
                    f"{peer_name}: …",
                    f"{senior_name}: (통화 종료)",
                ]
            elif theme == "언쟁":
                lines = [
                    f"{senior_name}: 자네가 내 이야기하고 다닌다며?",
                    f"{peer_name}: 누가 그런 말을 해? 오해야.",
                    f"{senior_name}: 오해라기엔 들은 사람이 여럿이야.",
                    f"{peer_name}: 난 그런 적 없어. 왜 나만 탓해?",
                    f"{senior_name}: 그럼 누가 그랬다는 거야.",
                    f"{peer_name}: 몰라. 근데 그렇게 몰아가면 서운해.",
                    f"{senior_name}: 나도 기분이 안 좋아.",
                    f"{peer_name}: 우리 차분히 이야기하자.",
                    f"{senior_name}: 그래, 일단 진정하자.",
                    f"{peer_name}: 다음에 만나서 정리하자.",
                    f"{senior_name}: 알겠네.",
                    f"{peer_name}: 응, 끊을게.",
                ]
            elif theme == "우울":
                lines = [
                    f"{senior_name}: 요즘은 그냥 아무것도 하기 싫어.",
                    f"{peer_name}: 무슨 일 있어? 목소리가 힘이 없네.",
                    f"{senior_name}: 자식들도 연락이 없고… 혼자인 느낌이야.",
                    f"{peer_name}: 그럴 때일수록 밖에 나가야지.",
                    f"{senior_name}: 다 귀찮아. 잠만 자고 싶어.",
                    f"{peer_name}: 밥은 먹었어?",
                    f"{senior_name}: 대충… 입맛도 없어.",
                    f"{peer_name}: 내일 내가 전화 다시 할게. 같이 산책하자.",
                    f"{senior_name}: 그래… 고맙다.",
                    f"{peer_name}: 혼자 견디지 말고 얘기해.",
                    f"{senior_name}: 응, 알겠어.",
                    f"{peer_name}: 오늘은 푹 쉬어.",
                ]
            elif theme == "건강":
                lines = [
                    f"{peer_name}: 무릎은 좀 어때? 비 오면 쑤시지 않아?",
                    f"{senior_name}: 어제 병원 갔다 왔지. 주사 맞았어.",
                    f"{peer_name}: 의사 선생님이 뭐래?",
                    f"{senior_name}: 당분간 무리하지 말라더라.",
                    f"{peer_name}: 스트레칭은 해?",
                    f"{senior_name}: 조금씩은 해보려고.",
                    f"{peer_name}: 따뜻하게 찜질도 해봐.",
                    f"{senior_name}: 그래야겠어. 고마워.",
                    f"{peer_name}: 약은 잘 챙겨 먹고?",
                    f"{senior_name}: 응, 알람 맞춰놨어.",
                    f"{peer_name}: 다음주에 같이 병원 갈까?",
                    f"{senior_name}: 괜찮아. 필요하면 연락할게.",
                ]
            elif theme == "취미":
                lines = [
                    f"{peer_name}: 어르신, 요즘 노래교실은 다니세요?",
                    f"{senior_name}: 응, 이번에 새 노래 배웠지.",
                    f"{peer_name}: 뭐 배웠어요?",
                    f"{senior_name}: 옛날 가요 한 곡. 부르면 기분이 좋아.",
                    f"{peer_name}: 봄 되면 꽃놀이도 가요.",
                    f"{senior_name}: 좋지. 사람들 만나면 힘이 나.",
                    f"{peer_name}: 사진도 많이 찍고요.",
                    f"{senior_name}: 그래, 우리 추억 남겨야지.",
                    f"{peer_name}: 다음 모임 때 같이 갈래요?",
                    f"{senior_name}: 그럼. 시간 알려줘.",
                    f"{peer_name}: 네, 문자 드릴게요.",
                    f"{senior_name}: 고맙네.",
                ]
            elif theme == "가족":
                lines = [
                    f"{senior_name}: 우리 손주가 이번에 취직했다더라.",
                    f"{peer_name}: 어머, 정말요? 축하드려요!",
                    f"{senior_name}: 용돈도 부쳐줬어. 마음이 참 고맙지.",
                    f"{peer_name}: 효자네요. 얼마나 예쁘실까.",
                    f"{senior_name}: 사진 보내왔는데 아주 든든하더라.",
                    f"{peer_name}: 건강만 잘 챙기시면 돼요.",
                    f"{senior_name}: 그래, 나도 오래 살아야지.",
                    f"{peer_name}: 다음에 손주 자랑 더 해주세요.",
                    f"{senior_name}: 하하, 알겠네.",
                    f"{peer_name}: 오늘은 좋은 꿈 꾸세요.",
                    f"{senior_name}: 고맙다. 너도 잘 자라.",
                    f"{peer_name}: 네, 안녕히 주무세요.",
                ]
            else:
                lines = [
                    f"{peer_name}: 안녕하세요, 어르신.",
                    f"{senior_name}: 어, 반갑네.",
                    f"{peer_name}: 오늘은 날씨가 좀 춥죠.",
                    f"{senior_name}: 그러게 말이야.",
                    f"{peer_name}: 식사는 하셨어요?",
                    f"{senior_name}: 응, 대충 먹었지.",
                    f"{peer_name}: 무리하지 마세요.",
                    f"{senior_name}: 고맙다.",
                    f"{peer_name}: 다음에 또 연락드릴게요.",
                    f"{senior_name}: 그래.",
                    f"{peer_name}: 안녕히 계세요.",
                    f"{senior_name}: 응.",
                ]
            return "\n".join(lines)

        call_created = analysis_created = transcript_created = 0

        for idx, (status, category, keywords, summary, peer_index, safe) in enumerate(
            call_templates, start=1
        ):
            session_id = f"sess-demo-{idx:03d}"
            peer = friend_objs[peer_index % len(friend_objs)]

            started_at = now - timedelta(days=(10 - idx), hours=idx)
            ended_at = started_at + timedelta(minutes=3 + idx, seconds=10 * idx)

            call, created = CallLog.objects.get_or_create(
                session_id=session_id,
                senior=demo_user,
                peer=peer,
                defaults={
                    "call_id": _uuid_for_field(CallLog, "call_id"),
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "created_at": ended_at,
                },
            )
            if created:
                call_created += 1

            _, a_created_flag = CallAnalysis.objects.get_or_create(
                call_log=call,
                defaults={
                    "status": status,
                    "category": category,
                    "keywords": keywords,
                    "summary": summary,
                    "created_at": ended_at,
                },
            )
            if a_created_flag:
                analysis_created += 1

            text = make_dialogue_lines(
                demo_user.name or "송민혁", peer.name or "상대방", category
            )
            _, t_created_flag = Transcript.objects.get_or_create(
                session_id=session_id,
                defaults={
                    "text": text,
                    "safe": safe,
                    "created_at": ended_at,
                },
            )
            if t_created_flag:
                transcript_created += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ call_logs (10) done (created={call_created})")
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ call_analyses (10) done (created={analysis_created})"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ transcripts (10) done (created={transcript_created})"
            )
        )

        self.stdout.write(self.style.SUCCESS("🎉 seed_dummy finished"))
