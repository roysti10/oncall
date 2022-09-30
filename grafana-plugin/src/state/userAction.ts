export enum UserAction {
  AlertGroupsRead = 'grafana-oncall-app.alert-groups:read',
  AlertGroupsWrite = 'grafana-oncall-app.alert-groups:write',

  AlertReceiveChannelsRead = 'grafana-oncall-app.alert-receive-channels:read',
  AlertReceiveChannelsWrite = 'grafana-oncall-app.alert-receive-channels:write',

  IntegrationsRead = 'grafana-oncall-app.integrations:read',
  IntegrationsWrite = 'grafana-oncall-app.integrations:write',

  EscalationChainsRead = 'grafana-oncall-app.escalation-chains:read',
  EscalationChainsWrite = 'grafana-oncall-app.escalation-chains:write',

  SchedulesRead = 'grafana-oncall-app.schedules:read',
  SchedulesWrite = 'grafana-oncall-app.schedules:write',

  ChatOpsRead = 'grafana-oncall-app.chatops:read',
  ChatOpsWrite = 'grafana-oncall-app.chatops:write',

  OutgoingWebhooksRead = 'grafana-oncall-app.outgoing-webhooks:read',
  OutgoingWebhooksWrite = 'grafana-oncall-app.outgoing-webhooks:write',

  MaintenanceRead = 'grafana-oncall-app.maintenance:read',
  MaintenanceWrite = 'grafana-oncall-app.maintenance:write',

  APIKeysRead = 'grafana-oncall-app.api-keys:read',
  APIKeysWrite = 'grafana-oncall-app.api-keys:write',

  OnCallShiftsRead = 'grafana-oncall-app.oncall-shifts:read',
  OnCallShiftsWrite = 'grafana-oncall-app.oncall-shifts:write',

  NotificationSettingsRead = 'grafana-oncall-app.notification-settings:read',
  NotificationSettingsWrite = 'grafana-oncall-app.notification-settings:write',

  GlobalSettingsRead = 'grafana-oncall-app.global-settings:read',
  GlobalSettingsWrite = 'grafana-oncall-app.global-settings:write',

  OwnSettingsRead = 'grafana-oncall-app.own-settings:read',
  OwnSettingsWrite = 'grafana-oncall-app.own-settings:write',

  OthersSettingsRead = 'grafana-oncall-app.others-settings:read',
  OthersSettingsWrite = 'grafana-oncall-app.others-settings:write',

  // These are not oncall specific
  OrganizationsRead = 'orgs:read',
  TeamsRead = 'teams:read',
  TeamsWrite = 'teams:write',
  UsersRead = 'users:read',
}

export type Permissions = Record<UserAction, boolean>;
