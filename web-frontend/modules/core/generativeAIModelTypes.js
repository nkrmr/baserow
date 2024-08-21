import { Registerable } from '@baserow/modules/core/registry'

export class GenerativeAIModelType extends Registerable {
  get name() {
    throw new Error('Must be set on the type.')
  }

  /**
   * Indicates whether files can be used as a knowledge base
   * for the prompt.
   */
  canPromptWithFiles() {
    return false
  }

  getOrder() {
    return 50
  }
}

const modelSettings = (label, description) => ({
  key: 'models',
  label,
  description,
  serialize: (value) => {
    return value
      .split(',')
      .map((model) => model.trim())
      .filter((model) => model !== '')
  },
  parse: (value) => {
    return Array.isArray(value) ? value.join(', ') : value
  },
})

export class OpenAIModelType extends GenerativeAIModelType {
  static getType() {
    return 'openai'
  }

  getName() {
    const { i18n } = this.app
    return i18n.t('generativeAIModelType.openai')
  }

  getSettings() {
    const { i18n } = this.app
    return [
      {
        key: 'api_key',
        label: i18n.t('generativeAIModelType.openaiApiKeyLabel'),
        description: i18n.t('generativeAIModelType.openaiApiKeyDescription'),
      },
      {
        key: 'organization',
        label: i18n.t('generativeAIModelType.openaiOrganization'),
      },
      modelSettings(
        i18n.t('generativeAIModelType.openaiModelsLabel'),
        i18n.t('generativeAIModelType.openaiModelsDescription')
      ),
    ]
  }

  canPromptWithFiles() {
    return true
  }

  getOrder() {
    return 10
  }
}

export class OllamaModelType extends GenerativeAIModelType {
  static getType() {
    return 'ollama'
  }

  getName() {
    const { i18n } = this.app
    return i18n.t('generativeAIModelType.ollama')
  }

  getSettings() {
    const { i18n } = this.app
    return [
      {
        key: 'host',
        label: i18n.t('generativeAIModelType.ollamaHostLabel'),
        description: i18n.t('generativeAIModelType.ollamaHostDescription'),
      },
      modelSettings(
        i18n.t('generativeAIModelType.ollamaModelsLabel'),
        i18n.t('generativeAIModelType.ollamaModelsDescription')
      ),
    ]
  }

  getOrder() {
    return 20
  }
}
