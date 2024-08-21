import path from 'path'

// Note that routes can't start with `/api/`, `/ws/` or `/media/` because they are
// reserved for the backend. In some cases, for example with the Heroku or Clouron
// deployment, the Baserow installation will share a single domain and port and then
// those URLS are forwarded to the backend or media files server. The rest is
// forwarded to the web-frontend.
export const routes = [
  {
    name: 'index',
    path: '',
    component: path.resolve(__dirname, 'pages/index.vue'),
  },
  {
    name: 'login',
    path: '/login',
    component: path.resolve(__dirname, 'pages/login.vue'),
  },
  {
    name: 'signup',
    path: '/signup',
    component: path.resolve(__dirname, 'pages/signup.vue'),
  },
  {
    name: 'forgot-password',
    path: '/forgot-password',
    component: path.resolve(__dirname, 'pages/forgotPassword.vue'),
  },
  {
    name: 'reset-password',
    path: '/reset-password/:token',
    component: path.resolve(__dirname, 'pages/resetPassword.vue'),
  },
  {
    name: 'verify-email-address',
    path: '/verify-email-address/:token',
    component: path.resolve(__dirname, 'pages/verifyEmailAddress.vue'),
  },
  {
    name: 'dashboard',
    path: '/dashboard',
    component: path.resolve(__dirname, 'pages/dashboard.vue'),
  },
  {
    name: 'group-invitation',
    path: '/group-invitation/:token',
    component: path.resolve(__dirname, 'pages/workspaceInvitation.vue'),
  }, // GroupDeprecation
  {
    name: 'workspace-invitation',
    path: '/workspace-invitation/:token',
    component: path.resolve(__dirname, 'pages/workspaceInvitation.vue'),
  },
  {
    name: 'admin-settings',
    path: '/admin/settings',
    component: path.resolve(__dirname, 'pages/admin/settings.vue'),
  },
  {
    name: 'admin-health',
    path: '/admin/health',
    component: path.resolve(__dirname, 'pages/admin/health.vue'),
  },
  {
    name: 'style-guide',
    path: '/style-guide',
    component: path.resolve(__dirname, 'pages/styleGuide.vue'),
  },
  {
    name: 'health-check',
    path: '/_health',
    component: path.resolve(__dirname, 'pages/_health.vue'),
  },
  {
    name: 'settings',
    path: '/settings/:workspaceId',
    component: path.resolve(__dirname, 'pages/settings.vue'),
    children: [
      {
        name: 'settings-members',
        path: 'members',
        component: path.resolve(__dirname, 'pages/settings/members.vue'),
      },
      {
        name: 'settings-invites',
        path: 'invites',
        component: path.resolve(__dirname, 'pages/settings/invites.vue'),
      },
    ],
  },
  {
    name: 'notification-redirect',
    path: '/notification/:workspaceId/:notificationId',
    component: path.resolve(__dirname, 'pages/notificationRedirect.vue'),
  },
  {
    name: 'onboarding',
    path: '/onboarding',
    component: path.resolve(__dirname, 'pages/onboarding.vue'),
  },
]

if (process.env.NODE_ENV !== 'production') {
  routes.push({
    name: 'storybook',
    path: '/storybook',
    component: path.resolve(__dirname, 'pages/storybook.vue'),
  })
}
