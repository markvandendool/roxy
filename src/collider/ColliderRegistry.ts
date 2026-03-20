export interface ColliderHitTarget {
  // Define properties of ColliderHitTarget here
}

class ColliderRegistry {
  private static instance: ColliderRegistry;
  private hitMap: Map<string, ColliderHitTarget>;

  private constructor() {
    this.hitMap = new Map();
  }

  public static getInstance(): ColliderRegistry {
    if (!ColliderRegistry.instance) {
      ColliderRegistry.instance = new ColliderRegistry();
    }
    return ColliderRegistry.instance;
  }

  public register(uuid: string, target: ColliderHitTarget): void {
    this.hitMap.set(uuid, target);
  }

  public get(uuid: string): ColliderHitTarget | undefined {
    return this.hitMap.get(uuid);
  }
}

export default ColliderRegistry;
