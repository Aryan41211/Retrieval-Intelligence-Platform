/**
 * Route guard.
 *
 * Redirects unauthenticated visitors to the login page, remembering where they
 * were headed so they land there after signing in. Renders nothing while the
 * initial session restore is still in flight, to avoid a login-page flash for
 * users who already have a valid session.
 */

import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Spinner } from '@/components/ui/Spinner';

export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center" aria-busy="true">
        <Spinner />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}

/**
 * Restrict a route to specific roles.
 *
 * Assumes the caller has already established authentication (nest inside
 * RequireAuth); an unauthorised user is sent to the dashboard rather than the
 * login page, because signing in again would not grant the missing role.
 */
export function RequireRole({
  roles,
  children,
}: {
  roles: string[];
  children: ReactNode;
}) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}
