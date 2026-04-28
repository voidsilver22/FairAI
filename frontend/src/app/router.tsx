import { createBrowserRouter, Navigate } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import NewAudit from '../pages/NewAudit';
import Dashboard from '../pages/Dashboard';
import Mitigation from '../pages/Mitigation';
import CounterfactualExplorer from '../pages/CounterfactualExplorer';
import Settings from '../pages/Settings';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout children={<Navigate to="/new-audit" replace />} />,
  },
  {
    path: '/new-audit',
    element: <Layout children={<NewAudit />} />,
  },
  {
    path: '/dashboard',
    element: <Layout children={<Dashboard />} />,
  },
  {
    path: '/mitigation/:jobId',
    element: <Layout children={<Mitigation />} />,
  },
  {
    path: '/scorecards',
    element: <Layout children={<CounterfactualExplorer />} />,
  },
  {
    path: '/settings',
    element: <Layout children={<Settings />} />,
  },
]);
