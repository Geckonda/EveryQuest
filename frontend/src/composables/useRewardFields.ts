import { computed, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCatalogStore } from '@/stores/catalog'
import { penaltyFor } from '@/utils/penalty'

interface RewardFields {
  tierId: number | null
  reward: number | null
  penalty: number | null
}

/**
 * Награда и штраф в формах квеста и шаблона: тир подставляет награду,
 * награда — штраф (× множитель из профиля), пока штраф не поправили вручную.
 */
export function useRewardFields(form: RewardFields) {
  const auth = useAuthStore()
  const catalog = useCatalogStore()

  const multiplier = computed(() => auth.user?.penalty_multiplier ?? 1)
  const penaltyTouched = ref(false)
  let filling = false

  const autoPenalty = (reward: number | null) =>
    reward === null ? null : penaltyFor(reward, multiplier.value)

  /** Заполняет поля при открытии формы. penalty = null — новый объект, штраф от награды. */
  function reset(tierId: number | null, reward: number | null, penalty: number | null) {
    filling = true
    form.tierId = tierId
    form.reward = reward
    form.penalty = penalty ?? autoPenalty(reward)
    // Штраф совпадает с расчётным — дальше он следует за наградой.
    penaltyTouched.value = penalty !== null && penalty !== autoPenalty(reward)
    filling = false
  }

  /** Обработчик ручного ввода штрафа: после него штраф больше не пересчитывается. */
  function setPenalty(value: number | null) {
    form.penalty = value
    penaltyTouched.value = true
  }

  /** Вернуть штраф к расчётному. */
  function resetPenalty() {
    penaltyTouched.value = false
    form.penalty = autoPenalty(form.reward)
  }

  // sync: иначе watcher сработает уже после reset(), когда флаг filling сброшен,
  // и затрёт награду редактируемого квеста наградой тира.
  watch(
    () => form.tierId,
    (tierId) => {
      if (filling) return
      const tier = catalog.tiers.find((t) => t.id === tierId)
      if (tier) form.reward = tier.default_reward
    },
    { flush: 'sync' },
  )

  watch(
    () => form.reward,
    (reward) => {
      if (!filling && !penaltyTouched.value) form.penalty = autoPenalty(reward)
    },
    { flush: 'sync' },
  )

  return { reset, setPenalty, resetPenalty, penaltyTouched }
}
