/** Space (top-level scope for threads and resources). */
export type SpaceType = "personal" | "workspace";

export interface Space {
  id: string;
  name: string;
  type: SpaceType;
}
