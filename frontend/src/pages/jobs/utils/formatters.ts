export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export const formatDateInChicagoTime = (dateString: string): { date: string; time: string } => {
  console.log('Original timestamp from backend:', dateString);

  let date: Date;

  if (!dateString.includes('Z') && !dateString.includes('+') && !dateString.match(/[-+]\d{2}:\d{2}$/)) {
    date = new Date(dateString + 'Z');
    console.log('Added Z for UTC, parsed as:', date.toISOString());
  } else {
    date = new Date(dateString);
  }

  const options: Intl.DateTimeFormatOptions = {
    timeZone: 'America/Chicago',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  };

  const formatter = new Intl.DateTimeFormat('en-US', options);
  const parts = formatter.formatToParts(date);

  const year = parts.find((p) => p.type === 'year')?.value || '';
  const month = parts.find((p) => p.type === 'month')?.value || '';
  const day = parts.find((p) => p.type === 'day')?.value || '';
  const hour = parts.find((p) => p.type === 'hour')?.value || '';
  const minute = parts.find((p) => p.type === 'minute')?.value || '';
  const second = parts.find((p) => p.type === 'second')?.value || '';

  const dateStr = `${month}/${day}/${year}`;
  const timeStr = `${hour}:${minute}:${second}`;

  console.log('Converted to Chicago time:', dateStr, timeStr);

  return { date: dateStr, time: timeStr };
};

export const getStatusColor = (
  status: string
): 'success' | 'warning' | 'error' | 'info' | 'default' => {
  switch (status) {
    case 'completed':
      return 'success';
    case 'processing':
      return 'warning';
    case 'failed':
      return 'error';
    case 'pending':
      return 'info';
    case 'cancelled':
    case 'canceled':
      return 'default';
    default:
      return 'default';
  }
};
