const DEFAULT_SPACE_URL = 'https://mk1647-argus.hf.space';

function normalizeSpaceUrl(value) {
  const raw = value?.trim() || DEFAULT_SPACE_URL;
  return raw.replace(/\/+$/, '');
}

const SPACE_URL = normalizeSpaceUrl(
  import.meta.env.VITE_HF_SPACE_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_ARGUS_API_URL
);

async function submitJob(apiName, data) {
  const response = await fetch(`${SPACE_URL}/gradio_api/call/${apiName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data }),
  });

  if (!response.ok) {
    throw new Error(`Space submission failed: ${response.status}`);
  }

  const payload = await response.json();
  if (!payload.event_id) {
    throw new Error('Space did not return an event id.');
  }
  return payload.event_id;
}

function tryParseJson(value) {
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

async function readJobResult(apiName, eventId) {
  const response = await fetch(`${SPACE_URL}/gradio_api/call/${apiName}/${eventId}`);
  if (!response.ok) {
    throw new Error(`Space result fetch failed: ${response.status}`);
  }

  const text = await response.text();
  const chunks = text
    .split('\n\n')
    .map((chunk) => chunk.trim())
    .filter(Boolean);

  for (let index = chunks.length - 1; index >= 0; index -= 1) {
    const event = chunks[index];
    const lines = event.split('\n');
    const eventType = lines.find((line) => line.startsWith('event:'))?.slice(6).trim();
    const dataLine = lines.find((line) => line.startsWith('data:'))?.slice(5).trim();

    if (eventType === 'complete' && dataLine) {
      const parsed = tryParseJson(dataLine);
      return Array.isArray(parsed) ? parsed[0] : parsed;
    }

    if (eventType === 'error' && dataLine) {
      throw new Error(typeof tryParseJson(dataLine) === 'string' ? tryParseJson(dataLine) : 'Space execution failed.');
    }
  }

  throw new Error('Space did not return a completed result.');
}

async function callSpace(apiName, inputs = []) {
  const eventId = await submitJob(apiName, inputs);
  return readJobResult(apiName, eventId);
}

export const api = {
  getSpaceInfo: () => ({
    name: 'mk1647/argus',
    spaceUrl: SPACE_URL,
  }),
  initialize: () => callSpace('initialize'),
  sensorAgent: ({ zoneId, sensorType, readingsJson }) =>
    callSpace('sensor_agent', [zoneId, sensorType, readingsJson]),
  permitAgent: ({ workType, zoneId, durationHours }) =>
    callSpace('permit_agent', [workType, zoneId, durationHours]),
  correlationAgent: ({ event1, event2, event3 }) =>
    callSpace('correlation_agent', [event1, event2, event3]),
  explainerAgent: ({ alertId, reasoningType }) =>
    callSpace('explainer_agent', [alertId, reasoningType]),
  orchestrator: ({ scenario }) => callSpace('orchestrator', [scenario]),
};
