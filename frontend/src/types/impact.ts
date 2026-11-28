import { z } from 'zod';

const status = z.enum(['potential', 'conditional', 'indeterminate', 'not_established', 'not_evaluated']);
const ids = z.array(z.string()).max(10);
const conclusion = z.object({
  status,
  justification: z.string(),
  conditions: z.array(z.string()),
  evidence: ids,
});
const point = z.object({ line: z.number().int().positive(), column: z.number().int().positive() });

export const impactSchema = z.object({
  version: z.literal('1.0'),
  coverage: z.enum(['syntax', 'correlated', 'partial', 'not_evaluated']),
  confidence: z.enum(['low', 'medium']),
  provenance: z.string(),
  limitations: z.array(z.string()),
  cia: z.object({ confidentiality: conclusion, integrity: conclusion, availability: conclusion }),
  resources: z.array(conclusion.extend({
    id: z.string().regex(/^SYS-(0[1-9]|1[0-5])$/),
    label: z.string(),
    operation: z.string(),
    scope: z.enum(['direct', 'correlated']),
  })).max(2),
  boundaries: z.array(conclusion.extend({
    id: z.string().regex(/^TB-(0[1-9]|10)$/),
    origin: z.string(),
    destination: z.string(),
  })).max(1),
  flows: z.array(z.object({
    source: z.string(),
    sink: z.string(),
    relationship: z.enum(['possible', 'indeterminate']),
    assignment_steps: z.number().int().nonnegative(),
  })).max(4),
  references: z.array(z.object({
    id: z.string(),
    role: z.enum(['instruction', 'source', 'sink', 'propagation', 'validation']),
    location: z.object({ start: point, end: point }),
    range: z.object({ start: z.number().int().nonnegative(), end: z.number().int().positive() }).nullable(),
    limitation: z.string(),
  })).max(10),
}).refine(impact => {
  const refs = new Set(impact.references.map(ref => ref.id));
  const conclusions = [...impact.resources, ...impact.boundaries, ...Object.values(impact.cia)];
  return refs.size === impact.references.length &&
    conclusions.every(item => item.evidence.every(id => refs.has(id))) &&
    impact.flows.every(flow => refs.has(flow.source) && refs.has(flow.sink)) &&
    impact.references.every(ref => !ref.range || ref.range.start < ref.range.end);
});

export type Impact = z.infer<typeof impactSchema>;
