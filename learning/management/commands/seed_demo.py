from django.core.management.base import BaseCommand

from learning.models import Question, Skill, Subject, Test, TestQuestion, Topic


class Command(BaseCommand):
    help = "Seed minimal QuestLab demo data."

    def handle(self, *args, **options):
        subjects = {}
        for title, slug, description in [
            ("Mathematics", "mathematics", "Math testing and diagnosis."),
            ("Physics", "physics", "Mechanics and conceptual physics tests."),
            ("Programming", "programming", "Coding and data structure assessments."),
            ("Chemistry", "chemistry", "Chemistry topic diagnostics."),
            ("Biology", "biology", "Biology learning checks."),
            ("English", "english", "Language and reading practice."),
        ]:
            subjects[slug], _ = Subject.objects.update_or_create(
                slug=slug,
                defaults={"title": title, "description": description},
            )

        math = subjects["mathematics"]
        topic_defs = [
            ("Arithmetic", "arithmetic"),
            ("Algebra", "algebra"),
            ("Geometry", "geometry"),
            ("Trigonometry", "trigonometry"),
            ("Calculus", "calculus"),
            ("Linear Algebra", "linear-algebra"),
            ("Probability", "probability"),
            ("Statistics", "statistics"),
            ("Differential Equations", "differential-equations"),
            ("Discrete Math", "discrete-math"),
        ]
        topics = {}
        for title, slug in topic_defs:
            topics[slug], _ = Topic.objects.update_or_create(
                subject=math,
                slug=slug,
                defaults={"title": title, "description": f"{title} tests and skill diagnosis."},
            )
        algebra = topics["algebra"]

        for subject_slug, title, slug in [
            ("physics", "Mechanics", "mechanics"),
            ("programming", "Arrays and Complexity", "arrays-complexity"),
            ("chemistry", "Atomic Structure", "atomic-structure"),
            ("biology", "Cell Biology", "cell-biology"),
            ("english", "Reading", "reading"),
        ]:
            Topic.objects.update_or_create(
                subject=subjects[subject_slug],
                slug=slug,
                defaults={"title": title, "description": f"{title} diagnostics."},
            )

        skills = {}
        for title, slug in [
            ("Quadratic factoring", "quadratic-factoring"),
            ("Zero product rule", "zero-product-rule"),
            ("Function evaluation", "function-evaluation"),
            ("Calculation accuracy", "calculation-accuracy"),
        ]:
            skills[slug], _ = Skill.objects.update_or_create(topic=algebra, slug=slug, defaults={"title": title})

        q1, _ = Question.objects.update_or_create(
            prompt=r"Solve the equation \(x^2 - 5x + 6 = 0\).",
            defaults={
                "subject": math,
                "topic": algebra,
                "type": Question.QuestionType.SINGLE_CHOICE,
                "difficulty": Question.Difficulty.BEGINNER,
                "options": [r"\(x=1,2\)", r"\(x=2,3\)", r"\(x=3,4\)", r"\(x=0,6\)"],
                "answer": r"\(x=2,3\)",
                "explanation": r"Factor \(x^2 - 5x + 6\) as \((x-2)(x-3)\).",
            },
        )
        q1.skills.set([skills["quadratic-factoring"], skills["zero-product-rule"]])

        q2, _ = Question.objects.update_or_create(
            prompt=r"If \(f(x)=2x+1\), find \(f(4)\).",
            defaults={
                "subject": math,
                "topic": algebra,
                "type": Question.QuestionType.SHORT_ANSWER,
                "difficulty": Question.Difficulty.BEGINNER,
                "options": [],
                "answer": "9",
                "explanation": r"Substitute \(x=4\): \(2\cdot4+1=9\).",
            },
        )
        q2.skills.set([skills["function-evaluation"], skills["calculation-accuracy"]])

        q3, _ = Question.objects.update_or_create(
            prompt=r"Solve \(3x + 5 = 20\).",
            defaults={
                "subject": math,
                "topic": algebra,
                "type": Question.QuestionType.SHORT_ANSWER,
                "difficulty": Question.Difficulty.BEGINNER,
                "options": [],
                "answer": "5",
                "explanation": r"Subtract 5 from both sides: \(3x=15\). Divide by 3: \(x=5\).",
            },
        )
        q3.skills.set([skills["calculation-accuracy"]])

        q4, _ = Question.objects.update_or_create(
            prompt=r"Solve the system: \(x + y = 7\) and \(x - y = 1\). Find \(x\).",
            defaults={
                "subject": math,
                "topic": algebra,
                "type": Question.QuestionType.SHORT_ANSWER,
                "difficulty": Question.Difficulty.INTERMEDIATE,
                "options": [],
                "answer": "4",
                "explanation": r"Add equations: \(2x=8\), so \(x=4\).",
            },
        )
        q4.skills.set([skills["function-evaluation"], skills["calculation-accuracy"]])

        q5, _ = Question.objects.update_or_create(
            prompt=r"If \(x + \frac{1}{x} = 3\), find \(x^2 + \frac{1}{x^2}\).",
            defaults={
                "subject": math,
                "topic": algebra,
                "type": Question.QuestionType.SINGLE_CHOICE,
                "difficulty": Question.Difficulty.ADVANCED,
                "options": ["5", "7", "9", "11"],
                "answer": "7",
                "explanation": r"Square both sides: \(x^2 + 2 + \frac{1}{x^2} = 9\), so \(x^2 + \frac{1}{x^2} = 7\).",
            },
        )
        q5.skills.set([skills["quadratic-factoring"], skills["calculation-accuracy"]])

        beginner, _ = Test.objects.update_or_create(
            slug="algebra-basics",
            defaults={
                "title": "Algebra Basics",
                "subject": math,
                "topic": algebra,
                "difficulty": Question.Difficulty.BEGINNER,
                "estimated_minutes": 8,
                "passing_score": 70,
            },
        )
        for order, question in enumerate([q1, q2], start=1):
            TestQuestion.objects.update_or_create(test=beginner, question=question, defaults={"order": order})

        beginner_2, _ = Test.objects.update_or_create(
            slug="linear-equations-basics",
            defaults={
                "title": "Linear Equations Basics",
                "subject": math,
                "topic": algebra,
                "difficulty": Question.Difficulty.BEGINNER,
                "estimated_minutes": 6,
                "passing_score": 70,
            },
        )
        for order, question in enumerate([q3, q2], start=1):
            TestQuestion.objects.update_or_create(test=beginner_2, question=question, defaults={"order": order})

        intermediate, _ = Test.objects.update_or_create(
            slug="algebra-functions",
            defaults={
                "title": "Algebra Functions",
                "subject": math,
                "topic": algebra,
                "difficulty": Question.Difficulty.INTERMEDIATE,
                "estimated_minutes": 10,
                "passing_score": 70,
            },
        )
        TestQuestion.objects.update_or_create(test=intermediate, question=q2, defaults={"order": 1})

        intermediate_2, _ = Test.objects.update_or_create(
            slug="algebra-systems",
            defaults={
                "title": "Systems of Equations",
                "subject": math,
                "topic": algebra,
                "difficulty": Question.Difficulty.INTERMEDIATE,
                "estimated_minutes": 10,
                "passing_score": 70,
            },
        )
        for order, question in enumerate([q4, q2], start=1):
            TestQuestion.objects.update_or_create(test=intermediate_2, question=question, defaults={"order": order})

        advanced, _ = Test.objects.update_or_create(
            slug="advanced-algebra-patterns",
            defaults={
                "title": "Advanced Algebra Patterns",
                "subject": math,
                "topic": algebra,
                "difficulty": Question.Difficulty.ADVANCED,
                "estimated_minutes": 14,
                "passing_score": 75,
            },
        )
        TestQuestion.objects.update_or_create(test=advanced, question=q1, defaults={"order": 1})

        advanced_2, _ = Test.objects.update_or_create(
            slug="algebra-identities-advanced",
            defaults={
                "title": "Advanced Algebra Identities",
                "subject": math,
                "topic": algebra,
                "difficulty": Question.Difficulty.ADVANCED,
                "estimated_minutes": 12,
                "passing_score": 75,
            },
        )
        for order, question in enumerate([q5, q1], start=1):
            TestQuestion.objects.update_or_create(test=advanced_2, question=question, defaults={"order": order})

        self.stdout.write(self.style.SUCCESS("Seeded demo data."))
