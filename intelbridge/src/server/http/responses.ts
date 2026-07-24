import { ZodError, type ZodType } from "zod";

export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    requestId: string;
  };
};

const safeErrorMessages: Record<string, string> = {
  CONNECTOR_NOT_FOUND: "Source connector not found.",
  CONNECTOR_NOT_RUNNABLE: "The source connector is not enabled.",
  DOCUMENT_NOT_FOUND: "Document not found.",
  INVALID_RUN_TRANSITION: "The run cannot transition from its current state.",
  MISSION_NOT_FOUND: "Research mission not found.",
  MISSION_NOT_RUNNABLE:
    "The mission must be ready, completed, or failed before it can run.",
  MISSION_SOURCE_REQUIRED:
    "Assign at least one connected source before starting research.",
  PROJECT_NOT_FOUND: "Project not found.",
  RUN_NOT_FOUND: "Research run not found.",
  RUN_ALREADY_ACTIVE: "This mission already has an active research run.",
  ALL_SOURCE_RETRIEVALS_FAILED:
    "No configured source could be retrieved for this run.",
  SOURCE_CONTENT_TOO_LARGE: "The source exceeds the configured size limit.",
  SOURCE_CONTENT_TYPE_UNSUPPORTED: "The source content type is not supported.",
  SOURCE_CONTENT_TYPE_MISMATCH:
    "The source content does not match its declared content type.",
  SOURCE_CONTENT_EMPTY: "The source does not contain readable content.",
  SOURCE_DNS_VALIDATION_FAILED:
    "The source hostname could not be validated as public.",
  SOURCE_FEED_INVALID:
    "The endpoint does not contain a valid RSS or Atom feed.",
  SOURCE_FILE_SIZE_INVALID: "The uploaded file is empty or too large.",
  SOURCE_FILE_NOT_FOUND: "The uploaded source object could not be found.",
  SOURCE_JSON_MALFORMED: "The source contains malformed JSON.",
  SOURCE_PDF_ENCRYPTED: "Encrypted PDFs are not supported.",
  SOURCE_PDF_MALFORMED: "The source is not a valid PDF.",
  SOURCE_PDF_TEXT_UNAVAILABLE: "No extractable text was found in the PDF.",
  SOURCE_REDIRECT_INVALID: "The source redirected to an invalid location.",
  SOURCE_RETRIEVAL_FAILED: "The source could not be retrieved.",
  SOURCE_URL_CREDENTIALS_FORBIDDEN:
    "Credentials are not permitted in source URLs.",
  SOURCE_URL_INVALID: "The source URL is invalid.",
  SOURCE_URL_PORT_FORBIDDEN: "The source URL uses a prohibited port.",
  SOURCE_URL_PRIVATE_NETWORK_FORBIDDEN:
    "Private and local network addresses are not permitted.",
  SOURCE_URL_PROTOCOL_UNSUPPORTED: "The source URL protocol is not supported.",
};

export function apiSuccess<T>(data: T, init?: ResponseInit) {
  return Response.json(
    {
      data,
      requestId: crypto.randomUUID(),
    },
    init,
  );
}

export function apiError(
  code: string,
  message: string,
  status: number,
  requestId = crypto.randomUUID(),
) {
  return Response.json({ error: { code, message, requestId } }, { status });
}

export function parseJsonBody<T>(schema: ZodType<T>, body: unknown) {
  return schema.parse(body);
}

export function safeApiError(error: unknown) {
  const requestId = crypto.randomUUID();

  if (error instanceof ZodError) {
    return apiError(
      "VALIDATION_ERROR",
      error.issues[0]?.message ?? "The request is invalid.",
      400,
      requestId,
    );
  }

  if (error instanceof Error) {
    const message = safeErrorMessages[error.message];
    if (message) {
      const notFound = error.message.endsWith("_NOT_FOUND");
      const conflict = [
        "INVALID_RUN_TRANSITION",
        "MISSION_SOURCE_REQUIRED",
        "RUN_ALREADY_ACTIVE",
      ].includes(error.message);
      return apiError(
        error.message,
        message,
        notFound ? 404 : conflict ? 409 : 400,
        requestId,
      );
    }
  }

  console.error(
    JSON.stringify({
      errorCode: "INTERNAL_ERROR",
      requestId,
      status: 500,
    }),
  );
  return apiError(
    "INTERNAL_ERROR",
    "IntelBridge could not complete the request.",
    500,
    requestId,
  );
}
