import { AdminSettings } from "../components/admin-settings";
import { DatasetBrowser } from "../components/dataset-browser";
import { NetworkView } from "../components/network-view";
import { UploadManager } from "../components/upload-manager";

export default function Page() {
  return (
    <div className="grid">
      <h1>openPIP 2.0 Portal</h1>
      <UploadManager />
      <DatasetBrowser />
      <NetworkView />
      <AdminSettings />
    </div>
  );
}
