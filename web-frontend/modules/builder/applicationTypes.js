import { ApplicationType } from '@baserow/modules/core/applicationTypes'
import BuilderForm from '@baserow/modules/builder/components/form/BuilderForm'
import SidebarComponentBuilder from '@baserow/modules/builder/components/sidebar/SidebarComponentBuilder'
import { populatePage } from '@baserow/modules/builder/store/page'
import PageTemplate from '@baserow/modules/builder/components/page/PageTemplate'
import PageTemplateSidebar from '@baserow/modules/builder/components/page/PageTemplateSidebar'

export class BuilderApplicationType extends ApplicationType {
  static getType() {
    return 'builder'
  }

  getIconClass() {
    return 'iconoir-apple-imac-2021'
  }

  getName() {
    const { i18n } = this.app
    return i18n.t('applicationType.builder')
  }

  getDefaultName() {
    const { i18n } = this.app
    return i18n.t('applicationType.builderDefaultName')
  }

  supportsTrash() {
    return false
  }

  getApplicationFormComponent() {
    return BuilderForm
  }

  getSidebarComponent() {
    return SidebarComponentBuilder
  }

  getTemplateSidebarComponent() {
    return PageTemplateSidebar
  }

  getTemplatesPageComponent() {
    return PageTemplate
  }

  populate(application) {
    const values = super.populate(application)
    values.pages = values.pages.map(populatePage)
    if (!values.integrations) {
      values.integrations = []
    }
    if (!values.userSources) {
      values.userSources = []
    }
    values._loadedOnce = false

    values.userSourceUser = null
    return values
  }

  delete(application, { $router }) {
    const pageSelected = application.pages.some((page) => page._.selected)
    if (pageSelected) {
      $router.push({ name: 'dashboard' })
    }
  }

  async loadExtraData(builder) {
    if (!builder._loadedOnce) {
      await Promise.all([
        this.app.store.dispatch('userSource/fetch', {
          application: builder,
        }),
        this.app.store.dispatch('integration/fetch', {
          application: builder,
        }),
      ])
      await this.app.store.dispatch('application/forceUpdate', {
        application: builder,
        data: { _loadedOnce: true },
      })
    }
  }

  async select(application, { $router, $i18n, $store }) {
    const pages = application.pages
      .map((p) => p)
      .sort((a, b) => a.order - b.order)

    if (pages.length > 0) {
      await $router.push({
        name: 'builder-page',
        params: {
          builderId: application.id,
          pageId: pages[0].id,
        },
      })
      return true
    } else {
      $store.dispatch('toast/error', {
        title: $i18n.t('applicationType.cantSelectPageTitle'),
        message: $i18n.t('applicationType.cantSelectPageDescription'),
      })
      return false
    }
  }

  prepareForStoreUpdate(application, data) {
    return data
  }
}
