import http from '../base';
import type { DashboardOverview, MessageTrend, PlatformStatistics } from '../types/dashboard';
import { API_WEBUI_PREFIX } from '../config';

const BASE = API_WEBUI_PREFIX

export function getDashboardOverview(): Promise<DashboardOverview> {
  return http.get(`${BASE}/dashboard/overview`);
}

export function getMessageTrend(days: number = 7): Promise<MessageTrend> {
  return http.get(`${BASE}/dashboard/message-trend`, { params: { days } });
}

export function getPlatformStatistics(): Promise<PlatformStatistics> {
  return http.get(`${BASE}/dashboard/platform-statistics`);
}
