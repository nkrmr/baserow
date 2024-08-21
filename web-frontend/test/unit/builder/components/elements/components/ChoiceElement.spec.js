import { TestApp } from '@baserow/test/helpers/testApp'
import ChoiceElement from '@baserow/modules/builder/components/elements/components/ChoiceElement.vue'

describe('ChoiceElement', () => {
  let testApp = null
  let store = null

  beforeAll(() => {
    testApp = new TestApp()
    store = testApp.store
  })

  afterEach(() => {
    testApp.afterEach()
  })

  const mountComponent = ({ props = {}, slots = {}, provide = {} }) => {
    return testApp.mount(ChoiceElement, {
      propsData: props,
      slots,
      provide,
    })
  }

  const mountComponentForElement = async (element) => {
    const builder = { id: 1, theme: { primary_color: '#ccc' } }
    const page = { id: 1, elements: [] }
    const workspace = {}
    const mode = 'public'
    const applicationContext = { builder, page, mode }

    store.dispatch('element/forceCreate', { page, element })

    const elementType = store.$registry.get('element', 'choice')

    const defaultValue = element.multiple ? [] : null
    const payload = {
      value: defaultValue,
      type: elementType.formDataType(element),
      isValid: elementType.isValid(element, defaultValue, applicationContext),
      touched: false,
    }

    store.dispatch('formData/setFormData', {
      page,
      elementId: element.id,
      payload,
    })

    const wrapper = await mountComponent({
      props: {
        element,
      },
      provide: {
        builder,
        page,
        mode,
        applicationContext: { builder, page, mode },
        element,
        workspace,
      },
    })
    return wrapper
  }

  test('as default', async () => {
    const wrapper = await mountComponentForElement({
      id: 42,
      defaultValue: '1',
      parent_element_id: null,
      type: 'choice',
      multiple: false,
      option_type: 'manual',
      show_as_dropdown: true,
      options: [],
    })

    expect(wrapper.element).toMatchSnapshot()
  })

  test('as manual dropdown', async () => {
    const wrapper = await mountComponentForElement({
      id: 42,
      defaultValue: '1',
      parent_element_id: null,
      type: 'choice',
      multiple: false,
      option_type: 'manual',
      show_as_dropdown: true,
      options: [
        { value: '1', name: 'First' },
        { value: '2', name: 'Second' },
      ],
    })

    expect(wrapper.element).toMatchSnapshot()
  })

  test('as manual radio', async () => {
    const wrapper = await mountComponentForElement({
      id: 42,
      defaultValue: '1',
      parent_element_id: null,
      type: 'choice',
      multiple: false,
      option_type: 'manual',
      show_as_dropdown: false,
      options: [
        { value: '1', name: 'First' },
        { value: '2', name: 'Second' },
      ],
    })

    expect(wrapper.element).toMatchSnapshot()
  })

  test('as manual checkboxes', async () => {
    const wrapper = await mountComponentForElement({
      id: 42,
      defaultValue: '1',
      parent_element_id: null,
      type: 'choice',
      multiple: true,
      option_type: 'manual',
      show_as_dropdown: false,
      options: [
        { value: '1', name: 'First' },
        { value: '2', name: 'Second' },
      ],
    })

    expect(wrapper.element).toMatchSnapshot()
  })
})
