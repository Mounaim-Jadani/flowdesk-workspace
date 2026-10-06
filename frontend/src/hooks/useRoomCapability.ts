import { useRoomsStore } from '../stores/roomsStore';

export const useRoomCapability = (roomId: string, cap: string) =>
  useRoomsStore((s) => (s.capabilities[roomId] ?? []).includes(cap));
