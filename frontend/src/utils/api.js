const API_BASE_URL = 'http://localhost:8000/api';

export async function uploadImage(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/imagery/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to upload satellite image');
  }

  return response.json();
}

export async function processImage(imageId, threshold = 0.5, forceClassical = false) {
  const response = await fetch(`${API_BASE_URL}/imagery/process`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      image_id: imageId,
      detection_threshold: parseFloat(threshold),
      force_classical: forceClassical,
    }),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to process satellite image');
  }

  return response.json();
}

export function getDownloadUrl(imageId, fileType) {
  return `${API_BASE_URL}/imagery/download/${imageId}/${fileType}`;
}
