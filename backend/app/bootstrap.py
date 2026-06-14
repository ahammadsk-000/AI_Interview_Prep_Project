"""Idempotent startup bootstrap: seed RBAC roles + starter coding challenges."""
from __future__ import annotations

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.domain.coding.enums import ChallengeDifficulty
from app.domain.identity.enums import ALL_ROLES
from app.models.coding import CodingChallenge, TestCase
from app.models.user import Role


async def seed_roles() -> None:
    async with AsyncSessionLocal() as session:
        existing = set(
            (await session.execute(select(Role.name))).scalars().all()
        )
        created = False
        for role_name in ALL_ROLES:
            if role_name not in existing:
                session.add(Role(name=role_name, description=f"{role_name.value} role"))
                created = True
        if created:
            await session.commit()


# Public starter challenges. Each test case is {args: [...positional], expected, hidden}.
# args map directly onto the entrypoint's positional parameters.
_STARTER_CHALLENGES: list[dict] = [
    {
        "slug": "two-sum",
        "title": "Two Sum",
        "difficulty": ChallengeDifficulty.MEDIUM,
        "entrypoint": "two_sum",
        "prompt": (
            "Given a list of integers `nums` and an integer `target`, return the indices "
            "[i, j] (i < j) of the two numbers that add up to target. Exactly one solution "
            "exists and you may not use the same element twice."
        ),
        "starter": "def two_sum(nums, target):\n    # return [i, j] summing to target\n    pass\n",
        "tags": ["array", "hash-map"],
        "cases": [
            ([[2, 7, 11, 15], 9], [0, 1], False),
            ([[3, 2, 4], 6], [1, 2], False),
            ([[3, 3], 6], [0, 1], True),
            ([[1, 5, 3, 7], 12], [1, 3], True),
        ],
    },
    {
        "slug": "reverse-string",
        "title": "Reverse String",
        "difficulty": ChallengeDifficulty.EASY,
        "entrypoint": "reverse_string",
        "prompt": "Return the input string `s` reversed.",
        "starter": "def reverse_string(s):\n    # return s reversed\n    pass\n",
        "tags": ["string"],
        "cases": [
            (["hello"], "olleh", False),
            (["PrepForge"], "egroFperP", False),
            ([""], "", True),
            (["racecar"], "racecar", True),
        ],
    },
    {
        "slug": "fizzbuzz",
        "title": "FizzBuzz",
        "difficulty": ChallengeDifficulty.EASY,
        "entrypoint": "fizzbuzz",
        "prompt": (
            "Return a list of strings for 1..n: 'Fizz' if divisible by 3, 'Buzz' if by 5, "
            "'FizzBuzz' if by both, otherwise the number as a string."
        ),
        "starter": "def fizzbuzz(n):\n    # return the FizzBuzz list for 1..n\n    pass\n",
        "tags": ["math", "warmup"],
        "cases": [
            ([5], ["1", "2", "Fizz", "4", "Buzz"], False),
            ([3], ["1", "2", "Fizz"], False),
            ([15], ["1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz",
                    "11", "Fizz", "13", "14", "FizzBuzz"], True),
            ([1], ["1"], True),
        ],
    },
    {
        "slug": "valid-palindrome",
        "title": "Valid Palindrome",
        "difficulty": ChallengeDifficulty.EASY,
        "entrypoint": "is_palindrome",
        "prompt": (
            "Return True if `s` is a palindrome considering only alphanumeric characters and "
            "ignoring case, otherwise False."
        ),
        "starter": "def is_palindrome(s):\n    # ignore case and non-alphanumeric characters\n    pass\n",
        "tags": ["string", "two-pointers"],
        "cases": [
            (["A man, a plan, a canal: Panama"], True, False),
            (["race a car"], False, False),
            ([" "], True, True),
            (["ab"], False, True),
        ],
    },
    {
        "slug": "maximum-subarray",
        "title": "Maximum Subarray",
        "difficulty": ChallengeDifficulty.MEDIUM,
        "entrypoint": "max_subarray",
        "prompt": (
            "Given an integer list `nums`, return the largest sum of any contiguous "
            "non-empty subarray (Kadane's algorithm)."
        ),
        "starter": "def max_subarray(nums):\n    # return the maximum contiguous subarray sum\n    pass\n",
        "tags": ["array", "dynamic-programming"],
        "cases": [
            ([[-2, 1, -3, 4, -1, 2, 1, -5, 4]], 6, False),
            ([[1]], 1, False),
            ([[5, 4, -1, 7, 8]], 23, True),
            ([[-1, -2, -3]], -1, True),
        ],
    },
]


async def seed_challenges() -> None:
    """Insert public starter coding challenges if none exist yet (idempotent)."""
    async with AsyncSessionLocal() as session:
        count = (await session.execute(select(func.count()).select_from(CodingChallenge))).scalar_one()
        if count:
            return
        for spec in _STARTER_CHALLENGES:
            session.add(
                CodingChallenge(
                    slug=spec["slug"],
                    title=spec["title"],
                    difficulty=spec["difficulty"],
                    prompt=spec["prompt"],
                    entrypoint=spec["entrypoint"],
                    starter_code={"python": spec["starter"]},
                    tags=spec["tags"],
                    is_public=True,
                    created_by=None,
                    test_cases=[
                        TestCase(
                            order_idx=i,
                            args=args,
                            expected_output={"value": expected},
                            is_hidden=hidden,
                            weight=1,
                        )
                        for i, (args, expected, hidden) in enumerate(spec["cases"])
                    ],
                )
            )
        await session.commit()
