import http from '../base';
import type { DashboardOverview } from '../types/dashboard';

export function getDashboardOverview(): Promise<DashboardOverview> {
  return http.get('/api/dashboard/overview');
}
