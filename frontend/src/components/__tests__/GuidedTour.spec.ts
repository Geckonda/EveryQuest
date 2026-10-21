import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import GuidedTour from '../GuidedTour.vue'
import type { TourStep } from '@/composables/useTour'

const steps: TourStep[] = [
  { title: 'Привет', text: 'Начало' },
  { target: 'purse', title: 'Кошель', text: 'Золото' },
  { title: 'Конец', text: 'Удачи' },
]

function mountTour() {
  return mount(GuidedTour, {
    props: { steps, open: true, 'onUpdate:open': () => {} },
    attachTo: document.body,
  })
}

const card = () => document.querySelector('.tour .card') as HTMLElement | null
const button = (text: string) =>
  [...document.querySelectorAll<HTMLButtonElement>('.tour button')].find((b) =>
    b.textContent?.includes(text),
  )

describe('GuidedTour', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('листает шаги и показывает прогресс', async () => {
    const wrapper = mountTour()
    await nextTick()
    expect(card()?.textContent).toContain('Привет')
    expect(card()?.textContent).toContain('1 / 3')
    expect(button('Назад')).toBeUndefined()

    button('Далее')!.click()
    await nextTick()
    expect(card()?.textContent).toContain('Кошель')

    button('Далее')!.click()
    await nextTick()
    expect(card()?.textContent).toContain('Конец')
    expect(button('Пропустить')).toBeUndefined() // на последнем — только «В путь!»
    expect(button('В путь!')).toBeDefined()
    wrapper.unmount()
  })

  it('подсвечивает видимый элемент с data-tour', async () => {
    // Два элемента с одной меткой (меню в шапке и в нижней панели) — берётся видимый.
    const hidden = document.createElement('span')
    hidden.dataset.tour = 'purse'
    hidden.getClientRects = () => [] as unknown as DOMRectList
    const visible = document.createElement('span')
    visible.dataset.tour = 'purse'
    visible.scrollIntoView = () => {}
    visible.getClientRects = () => [{}] as unknown as DOMRectList
    visible.getBoundingClientRect = () =>
      ({ top: 10, left: 20, width: 100, height: 30, bottom: 40, right: 120 }) as DOMRect
    document.body.append(hidden, visible)

    const wrapper = mountTour()
    button('Далее')!.click()
    await nextTick()
    await nextTick()

    const spotlight = document.querySelector('.tour .spotlight') as HTMLElement
    expect(spotlight.style.top).toBe('4px') // 10 − отступ 6
    expect(spotlight.style.width).toBe('112px') // 100 + 2 × 6
    wrapper.unmount()
  })

  it('«Пропустить» и Escape закрывают тур', async () => {
    const events: boolean[] = []
    const wrapper = mount(GuidedTour, {
      props: { steps, open: true, 'onUpdate:open': (v: boolean) => events.push(v) },
      attachTo: document.body,
    })
    await nextTick()
    button('Пропустить')!.click()
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(events).toEqual([false, false])
    wrapper.unmount()
  })
})
