export class ColliderRegistry {
  private static instance: ColliderRegistry;
  private registry: Map<string, any>;

  private constructor() {
    this.registry = new Map<string, any>();
  }

  public static getInstance(): ColliderRegistry {
    if (!ColliderRegistry.instance) {
      ColliderRegistry.instance = new ColliderRegistry();
    }
    return ColliderRegistry.instance;
  }

  public register(key: string, value: any): void {
    this.registry.set(key, value);
  }

  public get(key: string): any {
    return this.registry.get(key);
  }

  public has(key: string): boolean {
    return this.registry.has(key);
  }

  public remove(key: string): void {
    this.registry.delete(key);
  }
}
