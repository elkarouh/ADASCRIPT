# Timetable Soft Constraints — TODO

Implement incrementally. Each item touches: SA energy (`soft_score`/`delta_soft`),
the server's `computeSoftScore` equivalent, and the viewer's `computeSoftScore` JS + settings UI.

---

## ~~1. Even weekly distribution (avoid subject clustering)~~ ✓ DONE
Penalise a class having the same subject on consecutive days.
Example: Math on Mon+Tue+Wed is worse than Mon+Wed+Fri.
- SA: per (class, subject), count runs of consecutive days that have a lesson
- Weight: `weight_subject_daily_spread`

## ~~2. Hard subjects in the morning~~ ✓ DONE
Penalise Math/Science lessons in slots > N (configurable threshold, default 4).
User marks subjects as "heavy" in the editor.
- SA: per lesson, if subject is heavy and slot > morning_threshold → +1
- Weight: `weight_heavy_subject_morning`
- UI: tag subjects as heavy/light; add morning_threshold slider

## ~~3. No back-to-back heavy subjects per class~~ SKIPPED (max_consecutive already handles this)
Penalise two consecutive slots of different heavy subjects for the same class.
(Two Math in a row is already covered by max_consecutive_same_subj hard constraint.)
Example: Math slot 3 then Science slot 4 for Year7A → penalty.
- SA: per (class, day), scan consecutive slot pairs
- Weight: `weight_no_consecutive_heavy`

## ~~4. Balanced day per class~~ SKIPPED (covered by subject daily spread)
Penalise a class having more than K lessons on a single day (soft, not hard).
Encourages even spread across the week.
- SA: per (class, day), if count > daily_balance_threshold → excess²
- Weight: `weight_class_daily_balance`

## ~~5. Teacher preferred slots~~ ✓ DONE
Each teacher can mark preferred/avoided slots (morning vs afternoon).
Penalise lessons outside preferred window.
- UI: per-teacher slot preference grid (similar to unavailability grid)
- SA: per lesson, check teacher preference
- Weight: `weight_teacher_slot_preference`

## 6. Minimize room changes per class per day
Penalise each room switch a class makes within a day.
- SA: per (class, day), count distinct rooms used
- Weight: `weight_room_stability`

## 7. Paired subjects on different days
User can declare subject pairs that should not fall on the same day for the same class.
Example: History and Geography never on the same day.
- UI: subject-pair editor
- SA: per (class, day), check if both subjects of any pair appear
- Weight: `weight_subject_pairing`
