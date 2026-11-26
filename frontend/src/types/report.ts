import { severities } from '@nextgenai/ui';
import { z } from 'zod';

z.config({ jitless: true });

const point = z.object({ line: z.number().int().positive(), column: z.number().int().positive() });
const strings = z.array(z.string());
const finding = z.object({
  id: z.string().min(1),
  rule_id: z.string(),
  title: z.string(),
  severity: z.enum(severities),
  confidence: z.enum(['low', 'medium', 'high']),
  confidence_reason: z.string(),
  status: z.string(),
  instruction: z.string(),
  location: z.object({ start: point, end: point }),
  context: z.object({ before: strings, after: strings }),
  evidence: z.object({
    shared: z.string(),
    truncated: z.boolean(),
    original_available_in_this_report: z.literal(false),
    original: z.never().optional(),
    correlation: z.array(z.record(z.string(), z.unknown())),
  }),
  explanation: z.string(),
  recommendation: z.string(),
  verification_commands: strings,
  limitations: strings,
});

// Validate the fields consumed by the GUI. The Python serializer owns the full report schema.
export const reportSchema = z.object({
  schema_version: z.literal('1.0'),
  parser: z.string().min(1),
  sha256: z.string().regex(/^[0-9a-f]{64}$/),
  analyzed_at_utc: z.iso.datetime({ offset: true }),
  complete: z.boolean(),
  analysis_status: z.enum(['complete', 'incomplete']),
  incomplete_reasons: strings,
  redaction_applied: z.literal(true),
  limitations: strings,
  findings: z.array(finding),
}).refine(report => report.complete
  ? report.analysis_status === 'complete' && report.incomplete_reasons.length === 0
  : report.analysis_status === 'incomplete' && report.incomplete_reasons.length > 0);

export type Report = z.infer<typeof reportSchema>;
export type Finding = Report['findings'][number];
