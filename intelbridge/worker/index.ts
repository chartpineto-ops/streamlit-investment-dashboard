import {
  DEFAULT_DEVICE_SIZES,
  DEFAULT_IMAGE_SIZES,
  handleImageOptimization,
} from "vinext/server/image-optimization";
import handler from "vinext/server/app-router-entry";

interface ImageTransformer {
  input(stream: ReadableStream): {
    transform(options: Record<string, unknown>): {
      output(options: {
        format: string;
        quality: number;
      }): Promise<{ response(): Response }>;
    };
  };
}

interface WorkerEnvironment {
  ASSETS: {
    fetch(request: Request): Promise<Response>;
  };
  DB: unknown;
  IMAGES: ImageTransformer;
}

interface WorkerExecutionContext {
  passThroughOnException(): void;
  waitUntil(promise: Promise<unknown>): void;
}

const worker = {
  async fetch(
    request: Request,
    environment: WorkerEnvironment,
    context: WorkerExecutionContext,
  ) {
    const url = new URL(request.url);

    if (url.pathname === "/_vinext/image") {
      const allowedWidths = [...DEFAULT_DEVICE_SIZES, ...DEFAULT_IMAGE_SIZES];
      return handleImageOptimization(
        request,
        {
          fetchAsset: (path) =>
            environment.ASSETS.fetch(new Request(new URL(path, request.url))),
          transformImage: async (body, { format, quality, width }) => {
            const result = await environment.IMAGES.input(body)
              .transform(width > 0 ? { width } : {})
              .output({ format, quality });
            return result.response();
          },
        },
        allowedWidths,
      );
    }

    return handler.fetch(request, environment, context);
  },
};

export default worker;
