"use client";

import { Alert, Button, Space } from "antd";

export function ErrorState({ error, retry }: { error: string; retry?: () => void }) {
  return <Alert type="warning" showIcon message="Chưa thể tải dữ liệu" description={<Space direction="vertical"><span>{error}</span>{retry && <Button onClick={retry}>Thử lại</Button>}</Space>} />;
}

