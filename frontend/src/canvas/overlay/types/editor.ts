export enum EditorMode {
  CREATE = "CREATE", // Initial state: user drags to create bounds
  VIEW = "VIEW",     // Viewing mode: MapLibre renders the overlay
  EDIT = "EDIT",     // Editing mode: Canvas renders with transform handles
}
