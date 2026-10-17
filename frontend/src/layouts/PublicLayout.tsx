import { Outlet } from 'react-router-dom';

export default function PublicLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.18),_transparent_55%)] p-4">
      <Outlet />
    </div>
  );
}
