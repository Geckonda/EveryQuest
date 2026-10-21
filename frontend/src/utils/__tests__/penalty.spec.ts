import { describe, expect, it } from 'vitest'
import { penaltyFor } from '../penalty'

describe('penaltyFor', () => {
  // Те же случаи, что в backend/tests/test_quests.py::test_default_penalty.
  it.each([
    [10, 1, 10],
    [10, 2, 20],
    [25, 1.5, 38],
    [10, 0, 0],
    [1, 0.25, 0],
    [2, 0.25, 1],
    [1_000_000, 10, 1_000_000],
    [3, 1.15, 3], // 3.45 — без ошибок float
  ])('%i × %d → %i', (reward, multiplier, penalty) => {
    expect(penaltyFor(reward, multiplier)).toBe(penalty)
  })
})
