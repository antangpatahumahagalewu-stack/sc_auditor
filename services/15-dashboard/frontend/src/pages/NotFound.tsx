import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="text-8xl font-bold dark:text-[#27272a] light:text-[#e4e4e7]">404</div>
      <h2 className="text-2xl font-semibold mt-4">Page Not Found</h2>
      <p className="dark:text-[#a1a1aa] light:text-[#71717a] mt-2 mb-8">
        The page you're looking for doesn't exist.
      </p>
      <Link to="/" className="btn-primary">
        Back to Dashboard
      </Link>
    </div>
  );
}
