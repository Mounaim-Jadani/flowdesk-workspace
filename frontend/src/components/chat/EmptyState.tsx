import { MessageSquare, Users, Zap } from 'lucide-react';

export function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center bg-gray-900">
      <div className="text-center max-w-md px-6">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 mb-6">
          <MessageSquare className="w-10 h-10 text-white" />
        </div>

        <h2 className="text-2xl font-bold text-white mb-3">
          Welcome to ChatApp
        </h2>

        <p className="text-gray-400 mb-8">
          Select a conversation from the sidebar to start chatting, or create a new chat to connect with someone.
        </p>

        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="p-4 rounded-xl bg-gray-800 border border-gray-700">
            <Zap className="w-6 h-6 text-yellow-500 mx-auto mb-2" />
            <p className="text-sm text-gray-300">Real-time</p>
            <p className="text-xs text-gray-500">Instant messages</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-800 border border-gray-700">
            <Users className="w-6 h-6 text-green-500 mx-auto mb-2" />
            <p className="text-sm text-gray-300">Online Status</p>
            <p className="text-xs text-gray-500">See who's active</p>
          </div>
          <div className="p-4 rounded-xl bg-gray-800 border border-gray-700">
            <MessageSquare className="w-6 h-6 text-blue-500 mx-auto mb-2" />
            <p className="text-sm text-gray-300">Typing</p>
            <p className="text-xs text-gray-500">Live indicators</p>
          </div>
        </div>
      </div>
    </div>
  );
}
