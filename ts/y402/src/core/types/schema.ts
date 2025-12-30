import { z } from "zod";

/**
 * Schema for HTTP request input, excluding spec
 * and method which are handled by the middleware.
 */
export const HTTPInputSchema = z.object({
    queryParams: z.record(z.string()).optional(),
    bodyType: z
        .union([
            z.literal("json"),
            z.literal("form-data"),
            z.literal("multipart-form-data"),
            z.literal("text"),
            z.literal("binary"),
        ])
        .optional(),
    bodyFields: z.record(z.unknown()).optional(),
    headerFields: z.record(z.unknown()).optional(),
});

export type HTTPInput = z.infer<typeof HTTPInputSchema>;
