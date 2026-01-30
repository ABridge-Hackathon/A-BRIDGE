# app/common/management/commands/seed_dummy.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from app.friends.models import Friend
from app.care.models import CareRelation

# calls / transcripts 앱이 실제로 존재한다고 가정
from app.calls.models import CallLog, CallAnalysis
from app.transcripts.models import Transcript

import uuid
from datetime import date


class Command(BaseCommand):
    help = "Seed dummy data for ASCII backend"

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        now = timezone.now()

        # 1) Users
        users_data = [
            dict(
                phone_number="01012345678",
                name="김철수",
                gender="M",
                birth_year=1944,
                birth_date=date(1944, 5, 15),
                address="서울시 관악구 봉천동",
                profile_image_url="/images/profiles/user_main.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01098765432",
                name="최지민",
                gender="F",
                birth_year=1997,
                birth_date=date(1997, 8, 20),
                address="서울시 관악구 청룡동",
                profile_image_url="/images/profiles/worker_01.jpg",
                is_welfare_worker=True,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01011112222",
                name="박한길",
                gender="M",
                birth_year=1948,
                birth_date=date(1948, 3, 15),
                address="서울시 종로구 혜화동",
                profile_image_url="/images/profiles/user_m_01.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01033334444",
                name="최순자",
                gender="F",
                birth_year=1950,
                birth_date=date(1950, 11, 20),
                address="부산시 영도구 동삼동",
                profile_image_url="/images/profiles/user_f_01.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01055556666",
                name="이장수",
                gender="M",
                birth_year=1944,
                birth_date=date(1944, 2, 10),
                address="경기도 수원시 팔달구",
                profile_image_url="/images/profiles/user_m_02.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01077778888",
                name="김영희",
                gender="F",
                birth_year=1951,
                birth_date=date(1951, 7, 7),
                address="서울시 관악구 신림동",
                profile_image_url="/images/profiles/user_f_02.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=True,
            ),
            dict(
                phone_number="01000000000",
                name="(알수없음)",
                gender="M",
                birth_year=1980,
                birth_date=date(1980, 1, 1),
                address="불명",
                profile_image_url="/images/profiles/unknown.jpg",
                is_welfare_worker=False,
                is_active=True,
                is_phone_verified=False,
            ),
        ]

        created_count = 0
        for u in users_data:
            user, created = User.objects.get_or_create(
                phone_number=u["phone_number"],
                defaults={
                    **u,
                    "created_at": getattr(User, "created_at", None) and now or now,
                },
            )
            if created:
                # 비번 지정 (create_user 못 쓰는 경우 대비)
                user.set_password("test1234!")
                user.save()
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ users done (created={created_count})")
        )

        # 2) CareRelation (복지사 1명 -> 김철수 1명)
        worker = User.objects.get(phone_number="01098765432")
        senior = User.objects.get(phone_number="01012345678")
        CareRelation.objects.get_or_create(welfare_worker=worker, senior=senior)
        self.stdout.write(self.style.SUCCESS("✅ care_relations done"))

        # 3) Friends (김철수의 친구들)
        pairs = [
            ("01012345678", "01077778888"),
            ("01012345678", "01055556666"),
            ("01012345678", "01011112222"),
            ("01012345678", "01033334444"),
            ("01012345678", "01098765432"),
        ]
        f_created = 0
        for me_phone, friend_phone in pairs:
            me = User.objects.get(phone_number=me_phone)
            fr = User.objects.get(phone_number=friend_phone)
            _, created = Friend.objects.get_or_create(
                user=me,
                friend_user=fr,
                defaults={"created_at": now},
            )
            if created:
                f_created += 1
        self.stdout.write(self.style.SUCCESS(f"✅ friends done (created={f_created})"))

        # 4) CallLogs + CallAnalysis
        unknown = User.objects.get(phone_number="01000000000")
        safe_friend = User.objects.get(phone_number="01033334444")  # 최순자

        call_specs = [
            (
                "sess-001-danger",
                "DANGER",
                ["검찰", "계좌이체", "구속수사"],
                "기관 사칭 및 금전 요구 패턴 감지",
                unknown,
            ),
            (
                "sess-002-safe",
                "SAFE",
                ["경로당", "김치찜", "식사"],
                "일상적인 안부 대화",
                safe_friend,
            ),
            (
                "sess-003-danger",
                "DANGER",
                ["미친", "꺼져", "영감탱이"],
                "지속적인 폭언 및 비속어 감지",
                unknown,
            ),
        ]

        c_created = 0
        a_created = 0
        for session_id, status, keywords, summary, peer in call_specs:
            call, created = CallLog.objects.get_or_create(
                session_id=session_id,
                senior=senior,
                peer=peer,
                defaults={
                    "call_id": uuid.uuid4(),  # UUIDField이면 OK
                    "started_at": now,
                    "ended_at": now,
                    "created_at": now,
                },
            )
            if created:
                c_created += 1

            _, a_created_flag = CallAnalysis.objects.get_or_create(
                call_log=call,
                defaults={
                    "status": status,
                    "category": "AUTO",
                    "keywords": keywords,
                    "summary": summary,
                    "created_at": now,
                },
            )
            if a_created_flag:
                a_created += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ call_logs done (created={c_created})")
        )
        self.stdout.write(
            self.style.SUCCESS(f"✅ call_analyses done (created={a_created})")
        )

        # 5) Transcripts
        transcripts = [
            (
                "sess-001-danger",
                "상대방: 어르신, 서울중앙지검입니다. 통장이 범죄에 연루되었어요.",
                False,
            ),
            (
                "sess-002-safe",
                "최순자: 오라버니 식사는 하셨어요? 오늘 경로당 메뉴가 김치찜이래요.",
                True,
            ),
            (
                "sess-003-danger",
                "상대방: 야이 늙은이가 말을 못 알아들어? 귀 먹었어?",
                False,
            ),
        ]

        t_created = 0
        for sid, text, safe in transcripts:
            # session_id 단위로 중복 방지 (원하면 조건 바꿔도 됨)
            obj, created = Transcript.objects.get_or_create(
                session_id=sid,
                defaults={"text": text, "safe": safe, "created_at": now},
            )
            if created:
                t_created += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ transcripts done (created={t_created})")
        )

        self.stdout.write(self.style.SUCCESS("🎉 seed_dummy finished"))
