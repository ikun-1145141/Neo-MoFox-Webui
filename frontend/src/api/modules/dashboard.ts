import http from '../base';
import type { DashboardOverview, MessageTrend, PlatformStatistics } from '../types/dashboard';

export function getDashboardOverview(): Promise<DashboardOverview> {
  return http.get('/api/dashboard/overview');
}

export function getMessageTrend(days: number = 7): Promise<MessageTrend> {
  return http.get('/api/dashboard/message-trend', { params: { days } });
}

export function getPlatformStatistics(): Promise<PlatformStatistics> {
  return http.get('/api/dashboard/platform-statistics');
}
