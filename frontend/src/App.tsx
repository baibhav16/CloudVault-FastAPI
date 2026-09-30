import { useEffect, useState } from "react";
import "./styles.css";

const API = `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/v1`;

// ============================================================
// TYPES
// ============================================================

interface CloudFile {
  id: number;
  name: string;
  original_name: string;
  owner_id: number;
  folder_id: number | null;
  storage_key: string;
  size: number;
  content_type: string;
  deleted: boolean;
  created_at: string;
  updated_at: string;
  current_version: number;
}

interface Folder {
  id: number;
  name: string;
  owner_id: number;
  parent_folder_id: number | null;
}

interface User {
  id: number;
  name: string;
  email: string;
  role: string;
}

interface SharedFile {
  share_id: number;
  file_id: number;
  name: string;
  original_name: string;
  size: number;
  content_type: string;
  permission: "VIEWER" | "EDITOR";
  owner_id: number;
  owner_name: string;
  owner_email: string;
  created_at: string;
}

interface FileVersion {
  id: number;
  file_id: number;
  version_number: number;
  size: number;
  created_at: string;
  is_current: boolean;
}

type View = "drive" | "shared" | "trash";

// ============================================================
// APP
// ============================================================

export default function App() {
  // ==========================================================
  // AUTH
  // ==========================================================

  const [token, setToken] = useState(
    localStorage.getItem("token") || ""
  );

  const [user, setUser] = useState<User | null>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // ==========================================================
  // DRIVE
  // ==========================================================

  const [files, setFiles] = useState<CloudFile[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);

  const [currentFolder, setCurrentFolder] =
    useState<number | null>(null);

  const [view, setView] = useState<View>("drive");

  const [search, setSearch] = useState("");

  // ==========================================================
  // SHARED FILES
  // ==========================================================

  const [sharedFiles, setSharedFiles] =
    useState<SharedFile[]>([]);

  const [showShareModal, setShowShareModal] =
    useState(false);

  const [shareFile, setShareFile] =
    useState<CloudFile | null>(null);

  const [shareEmail, setShareEmail] =
    useState("");

  const [sharePermission, setSharePermission] =
    useState<"VIEWER" | "EDITOR">("VIEWER");

  // ==========================================================
  // VERSIONING
  // ==========================================================

  const [versions, setVersions] =
    useState<FileVersion[]>([]);

  const [versionFile, setVersionFile] =
    useState<CloudFile | null>(null);

  const [showVersionModal, setShowVersionModal] =
    useState(false);

  // ==========================================================
  // UI
  // ==========================================================

  const [message, setMessage] =
    useState("");

  const [showFolderInput, setShowFolderInput] =
    useState(false);

  const [folderName, setFolderName] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  // ==========================================================
  // API HELPER
  // ==========================================================

  async function api(
    endpoint: string,
    options: RequestInit = {}
  ) {
    const headers: HeadersInit = {
      ...(options.body instanceof FormData
        ? {}
        : {
            "Content-Type": "application/json",
          }),

      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),

      ...(options.headers || {}),
    };

    return fetch(`${API}${endpoint}`, {
      ...options,
      headers,
    });
  }

  // ==========================================================
  // LOAD USER
  // ==========================================================

  async function loadUser() {
    try {
      const response = await api("/auth/me");

      if (!response.ok) {
        logout();
        return;
      }

      const data: User =
        await response.json();

      setUser(data);
    } catch {
      setMessage(
        "Unable to connect to backend"
      );
    }
  }

  // ==========================================================
  // LOAD FILES
  // ==========================================================

  async function loadFiles() {
    if (!token || view !== "drive") {
      return;
    }

    try {
      setLoading(true);

      const params =
        new URLSearchParams();

      if (currentFolder !== null) {
        params.append(
          "folder_id",
          currentFolder.toString()
        );
      }

      if (search.trim()) {
        params.append(
          "search",
          search.trim()
        );
      }

      const query =
        params.toString();

      const endpoint = query
        ? `/files?${query}`
        : "/files";

      const response =
        await api(endpoint);

      if (!response.ok) {
        if (response.status === 401) {
          logout();
          return;
        }

        const data =
          await response.json().catch(
            () => ({})
          );

        setMessage(
          data.detail ||
            "Could not load files"
        );

        return;
      }

      const data: CloudFile[] =
        await response.json();

      setFiles(data);
    } catch {
      setMessage(
        "Unable to connect to backend"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // LOAD FOLDERS
  // ==========================================================

  async function loadFolders() {
    if (!token) {
      return;
    }

    try {
      const response =
        await api("/folders");

      if (!response.ok) {
        return;
      }

      const data: Folder[] =
        await response.json();

      setFolders(data);
    } catch {
      setMessage(
        "Could not load folders"
      );
    }
  }

  // ==========================================================
  // LOAD TRASH
  // ==========================================================

  async function loadTrash() {
    if (!token) {
      return;
    }

    try {
      setLoading(true);

      const response =
        await api("/files/trash");

      if (!response.ok) {
        const data =
          await response.json().catch(
            () => ({})
          );

        setMessage(
          data.detail ||
            "Could not load Trash"
        );

        return;
      }

      const data: CloudFile[] =
        await response.json();

      setFiles(data);
    } catch {
      setMessage(
        "Unable to load Trash"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // LOAD SHARED FILES
  // ==========================================================

  async function loadSharedFiles() {
    if (!token) {
      return;
    }

    try {
      setLoading(true);

      const response =
        await api("/shares/files");

      if (!response.ok) {
        const data =
          await response.json().catch(
            () => ({})
          );

        setMessage(
          data.detail ||
            "Could not load shared files"
        );

        return;
      }

      const data: SharedFile[] =
        await response.json();

      setSharedFiles(data);
    } catch {
      setMessage(
        "Unable to load shared files"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // INITIAL LOAD
  // ==========================================================

  useEffect(() => {
    if (!token) {
      return;
    }

    loadUser();
    loadFolders();
  }, [token]);

  // ==========================================================
  // VIEW / FOLDER / SEARCH
  // ==========================================================

  useEffect(() => {
    if (!token) {
      return;
    }

    if (view === "drive") {
      loadFiles();
    } else if (view === "trash") {
      loadTrash();
    } else if (view === "shared") {
      loadSharedFiles();
    }
  }, [
    token,
    view,
    currentFolder,
    search,
  ]);

  // ==========================================================
  // REGISTER
  // ==========================================================

  async function register() {
    if (!name.trim()) {
      setMessage(
        "Please enter your name"
      );
      return;
    }

    if (!email.trim()) {
      setMessage(
        "Please enter your email"
      );
      return;
    }

    if (password.length < 8) {
      setMessage(
        "Password must contain at least 8 characters"
      );
      return;
    }

    try {
      setLoading(true);

      const response =
        await fetch(
          `${API}/auth/register`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              name,
              email,
              password,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        setMessage(
          data.detail ||
            "Registration failed"
        );

        return;
      }

      setMessage(
        "Account created successfully. You can now login."
      );

      setPassword("");
    } catch {
      setMessage(
        "Unable to connect to backend"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // LOGIN
  // ==========================================================

  async function login() {
    if (!email.trim()) {
      setMessage(
        "Please enter your email"
      );
      return;
    }

    if (!password) {
      setMessage(
        "Please enter your password"
      );
      return;
    }

    try {
      setLoading(true);

      const response =
        await fetch(
          `${API}/auth/login`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              email,
              password,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        setMessage(
          data.detail ||
            "Invalid email or password"
        );

        return;
      }

      localStorage.setItem(
        "token",
        data.access_token
      );

      setToken(
        data.access_token
      );

      setUser(
        data.user || null
      );

      setMessage("");

      setEmail("");
      setPassword("");
    } catch {
      setMessage(
        "Unable to connect to backend"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // LOGOUT
  // ==========================================================

  function logout() {
    localStorage.removeItem(
      "token"
    );

    setToken("");

    setUser(null);

    setFiles([]);

    setFolders([]);

    setSharedFiles([]);

    setVersions([]);

    setCurrentFolder(null);

    setView("drive");

    setMessage("");
  }

  // ==========================================================
  // UPLOAD FILE
  // ==========================================================

  async function uploadFile(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    const selectedFile =
      event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    try {
      setLoading(true);

      const formData =
        new FormData();

      formData.append(
        "uploaded_file",
        selectedFile
      );

      if (currentFolder !== null) {
        formData.append(
          "folder_id",
          currentFolder.toString()
        );
      }

      setMessage(
        `Uploading ${selectedFile.name}...`
      );

      const response =
        await api(
          "/files/upload",
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        setMessage(
          data.detail ||
            "Upload failed"
        );

        return;
      }

      setMessage(
        `${selectedFile.name} uploaded successfully`
      );

      await loadFiles();
    } catch {
      setMessage(
        "Upload failed"
      );
    } finally {
      setLoading(false);
      event.target.value = "";
    }
  }

  // ==========================================================
  // DOWNLOAD FILE
  // ==========================================================

  async function downloadFile(
    file: CloudFile
  ) {
    try {
      setLoading(true);

      setMessage(
        `Downloading ${file.name}...`
      );

      const response =
        await api(
          `/files/${file.id}/download`
        );

      if (!response.ok) {
        const data =
          await response.json().catch(
            () => ({})
          );

        setMessage(
          data.detail ||
            "Download failed"
        );

        return;
      }

      const blob =
        await response.blob();

      downloadBlob(
        blob,
        file.original_name
      );

      setMessage(
        `${file.name} downloaded`
      );
    } catch {
      setMessage(
        "Download failed"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // DOWNLOAD SHARED FILE
  // ==========================================================

  async function downloadSharedFile(
    file: SharedFile
  ) {
    try {
      setLoading(true);

      setMessage(
        `Downloading ${file.name}...`
      );

      const response =
        await api(
          `/files/${file.file_id}/download`
        );

      if (!response.ok) {
        const data =
          await response.json().catch(
            () => ({})
          );

        setMessage(
          data.detail ||
            "You don't have permission to download this file"
        );

        return;
      }

      const blob =
        await response.blob();

      downloadBlob(
        blob,
        file.original_name
      );

      setMessage(
        `${file.name} downloaded`
      );
    } catch {
      setMessage(
        "Download failed"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // DOWNLOAD HELPER
  // ==========================================================

  function downloadBlob(
    blob: Blob,
    filename: string
  ) {
    const url =
      window.URL.createObjectURL(
        blob
      );

    const link =
      document.createElement(
        "a"
      );

    link.href = url;

    link.download =
      filename;

    document.body.appendChild(
      link
    );

    link.click();

    link.remove();

    window.URL.revokeObjectURL(
      url
    );
  }

  // ==========================================================
  // CREATE FOLDER
  // ==========================================================

  async function createFolder() {
    if (!folderName.trim()) {
      setMessage(
        "Enter a folder name"
      );

      return;
    }

    try {
      setLoading(true);

      const response =
        await api(
          "/folders",
          {
            method: "POST",
            body: JSON.stringify({
              name:
                folderName.trim(),
              parent_folder_id:
                currentFolder,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        setMessage(
          data.detail ||
            "Could not create folder"
        );

        return;
      }

      setFolderName("");

      setShowFolderInput(false);

      setMessage(
        `Folder "${data.name}" created successfully`
      );

      await loadFolders();
    } catch {
      setMessage(
        "Could not create folder"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // OPEN FOLDER
  // ==========================================================

  function openFolder(
    folderId: number
  ) {
    setView("drive");
    setSearch("");
    setCurrentFolder(folderId);
    setMessage("");
  }

  // ==========================================================
  // ROOT
  // ==========================================================

  function goToRoot() {
    setView("drive");
    setCurrentFolder(null);
    setSearch("");
    setMessage("");
  }

  // ==========================================================
  // DELETE
  // ==========================================================

  async function deleteFile(
    fileId: number
  ) {
    const confirmed =
      window.confirm(
        "Move this file to Trash?"
      );

    if (!confirmed) {
      return;
    }

    try {
      setLoading(true);

      const response =
        await api(
          `/files/${fileId}`,
          {
            method: "DELETE",
          }
        );

      if (!response.ok) {
        const data =
          await response.json().catch(
            () => ({})
          );

        setMessage(
          data.detail ||
            "Could not delete file"
        );

        return;
      }

      setMessage(
        "File moved to Trash"
      );

      await loadFiles();
    } catch {
      setMessage(
        "Could not delete file"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // RESTORE
  // ==========================================================

  async function restoreFile(
    fileId: number
  ) {
    try {
      setLoading(true);

      const response =
        await api(
          `/files/${fileId}/restore`,
          {
            method: "PATCH",
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        setMessage(
          data.detail ||
            "Could not restore file"
        );

        return;
      }

      setMessage(
        `${data.name} restored successfully`
      );

      await loadTrash();
    } catch {
      setMessage(
        "Could not restore file"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // PERMANENT DELETE
  // ==========================================================

  async function permanentlyDeleteFile(
    fileId: number
  ) {
    const confirmed =
      window.confirm(
        "This will permanently delete the file. Continue?"
      );

    if (!confirmed) {
      return;
    }

    try {
      setLoading(true);

      const response =
        await api(
          `/files/${fileId}/permanent`,
          {
            method: "DELETE",
          }
        );

      if (!response.ok) {
        const data =
          await response.json().catch(
            () => ({})
          );

        setMessage(
          data.detail ||
            "Could not permanently delete file"
        );

        return;
      }

      setMessage(
        "File permanently deleted"
      );

      await loadTrash();
    } catch {
      setMessage(
        "Could not permanently delete file"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // SHARE MODAL
  // ==========================================================

  function openShareModal(
    file: CloudFile
  ) {
    setShareFile(file);
    setShareEmail("");
    setSharePermission("VIEWER");
    setShowShareModal(true);
    setMessage("");
  }

  function closeShareModal() {
    setShowShareModal(false);
    setShareFile(null);
    setShareEmail("");
    setSharePermission("VIEWER");
  }

  // ==========================================================
  // SHARE FILE
  // ==========================================================

  async function submitShare() {
    if (!shareFile) {
      return;
    }

    if (!shareEmail.trim()) {
      setMessage(
        "Enter the user's email"
      );

      return;
    }

    try {
      setLoading(true);

      const response =
        await api(
          `/shares/files/${shareFile.id}`,
          {
            method: "POST",
            body: JSON.stringify({
              email:
                shareEmail.trim(),
              permission:
                sharePermission,
            }),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        setMessage(
          data.detail ||
            "Could not share file"
        );

        return;
      }

      closeShareModal();

      setMessage(
        `${shareFile.name} shared successfully`
      );
    } catch {
      setMessage(
        "Could not share file"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // VERSION HISTORY
  // ==========================================================

  async function loadVersions(
    fileId: number
  ) {
    try {
      setLoading(true);

      const response =
        await api(
          `/versions/${fileId}`
        );

      const data =
        await response.json();

      if (!response.ok) {
        setMessage(
          data.detail ||
            "Could not load versions"
        );

        return;
      }

      setVersions(data);
    } catch {
      setMessage(
        "Could not load version history"
      );
    } finally {
      setLoading(false);
    }
  }

  async function openVersionHistory(
    file: CloudFile
  ) {
    setVersionFile(file);

    setVersions([]);

    setShowVersionModal(true);

    await loadVersions(
      file.id
    );
  }

  function closeVersionHistory() {
    setShowVersionModal(false);
    setVersionFile(null);
    setVersions([]);
  }

  // ==========================================================
  // UPLOAD NEW VERSION
  // ==========================================================

  async function uploadNewVersion(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    if (!versionFile) {
      return;
    }

    const selectedFile =
      event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    try {
      setLoading(true);

      const formData =
        new FormData();

      formData.append(
        "uploaded_file",
        selectedFile
      );

      const response =
        await api(
          `/versions/${versionFile.id}`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        setMessage(
          data.detail ||
            "Could not upload new version"
        );

        return;
      }

      setMessage(
        `Version ${data.version_number} uploaded successfully`
      );

      await loadVersions(
        versionFile.id
      );

      await loadFiles();
    } catch {
      setMessage(
        "Could not upload new version"
      );
    } finally {
      setLoading(false);
      event.target.value = "";
    }
  }

  // ==========================================================
  // DOWNLOAD VERSION
  // ==========================================================

  async function downloadVersion(
    version: FileVersion
  ) {
    if (!versionFile) {
      return;
    }

    try {
      setLoading(true);

      const response =
        await api(
          `/versions/${versionFile.id}/${version.id}/download`
        );

      if (!response.ok) {
        const data =
          await response.json().catch(
            () => ({})
          );

        setMessage(
          data.detail ||
            "Could not download version"
        );

        return;
      }

      const blob =
        await response.blob();

      let originalName =
        versionFile.original_name;

      // Remove an accidental .vN suffix
      originalName =
        originalName.replace(
          /\.v\d+$/i,
          ""
        );

      const lastDot =
        originalName.lastIndexOf(".");

      let filename: string;

      if (
        lastDot > 0 &&
        lastDot < originalName.length - 1
      ) {
        const name =
          originalName.substring(
            0,
            lastDot
          );

        const extension =
          originalName.substring(
            lastDot
          );

        filename =
          `${name} (Version ${version.version_number})${extension}`;
      } else {
        filename =
          `${originalName} (Version ${version.version_number})`;
      }

      downloadBlob(
        blob,
        filename
      );
    } catch {
      setMessage(
        "Could not download version"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // RESTORE VERSION
  // ==========================================================

  async function restoreVersion(
    version: FileVersion
  ) {
    if (!versionFile) {
      return;
    }

    const confirmed =
      window.confirm(
        `Restore version ${version.version_number}?`
      );

    if (!confirmed) {
      return;
    }

    try {
      setLoading(true);

      const response =
        await api(
          `/versions/${versionFile.id}/${version.id}/restore`,
          {
            method: "POST",
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        setMessage(
          data.detail ||
            "Could not restore version"
        );

        return;
      }

      setMessage(
        `Version ${version.version_number} restored as a new version`
      );

      await loadVersions(
        versionFile.id
      );

      await loadFiles();
    } catch {
      setMessage(
        "Could not restore version"
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // AUTH SCREEN
  // ==========================================================

  if (!token) {
    return (
      <main className="auth">

        <section className="card">

          <p className="eyebrow">
            CLOUDVAULT
          </p>

          <h1>
            Secure cloud storage.
          </h1>

          <p className="muted">
            Store, organize and share
            your files securely.
          </p>

          <label>
            Name
          </label>

          <input
            value={name}
            onChange={(event) =>
              setName(
                event.target.value
              )
            }
            placeholder="Your name"
          />

          <label>
            Email
          </label>

          <input
            value={email}
            onChange={(event) =>
              setEmail(
                event.target.value
              )
            }
            placeholder="you@example.com"
          />

          <label>
            Password
          </label>

          <input
            type="password"
            value={password}
            onChange={(event) =>
              setPassword(
                event.target.value
              )
            }
            placeholder="Minimum 8 characters"
            onKeyDown={(event) => {
              if (
                event.key ===
                "Enter"
              ) {
                login();
              }
            }}
          />

          <div className="actions">

            <button
              onClick={login}
              disabled={loading}
            >
              {loading
                ? "Please wait..."
                : "Login"}
            </button>

            <button
              className="secondary"
              onClick={register}
              disabled={loading}
            >
              Create account
            </button>

          </div>

          {message && (
            <p className="message">
              {message}
            </p>
          )}

        </section>

      </main>
    );
  }

  // ==========================================================
  // CURRENT FOLDER
  // ==========================================================

  const currentFolderObject =
    currentFolder !== null
      ? folders.find(
          (folder) =>
            folder.id ===
            currentFolder
        )
      : null;

  // ==========================================================
  // VISIBLE FOLDERS
  // ==========================================================

  const visibleFolders =
    view === "drive"
      ? folders.filter(
          (folder) =>
            folder.parent_folder_id ===
            currentFolder
        )
      : [];

  // ==========================================================
  // DASHBOARD
  // ==========================================================

  return (
    <div className="dashboard">

      {/* ======================================================
          NAVBAR
      ====================================================== */}

      <header className="navbar">

        <div className="brand">
          ☁ CLOUDVAULT
        </div>

        <div className="user-area">

          <span>
            {user?.name || "User"}
          </span>

          <button
            className="logout"
            onClick={logout}
          >
            Logout
          </button>

        </div>

      </header>


      <div className="dashboard-body">

        {/* ====================================================
            SIDEBAR
        ==================================================== */}

        <aside className="sidebar">

          <button
            className={
              view === "drive"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={goToRoot}
          >
            🏠 My Drive
          </button>


          <button
            className={
              view === "shared"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => {
              setView("shared");
              setCurrentFolder(null);
              setSearch("");
              loadSharedFiles();
            }}
          >
            ⭐ Shared
          </button>


          <button
            className={
              view === "trash"
                ? "nav-item active"
                : "nav-item"
            }
            onClick={() => {
              setView("trash");
              setCurrentFolder(null);
              setSearch("");
              loadTrash();
            }}
          >
            🗑 Trash
          </button>


          {view === "drive" && (
            <div className="sidebar-section">

              <h4>
                Folders
              </h4>

              {folders
                .filter(
                  (folder) =>
                    folder.parent_folder_id ===
                    null
                )
                .map(
                  (folder) => (

                    <button
                      key={folder.id}
                      className={
                        currentFolder ===
                        folder.id
                          ? "folder-item selected"
                          : "folder-item"
                      }
                      onClick={() =>
                        openFolder(
                          folder.id
                        )
                      }
                    >
                      📁{" "}
                      {folder.name}
                    </button>

                  )
                )}

            </div>
          )}

        </aside>


        {/* ====================================================
            MAIN
        ==================================================== */}

        <main className="main-content">

          {/* ==================================================
              HEADER
          ================================================== */}

          <div className="content-header">

            <div>

              <p className="eyebrow">

                {view === "trash"
                  ? "TRASH"
                  : view === "shared"
                    ? "SHARED WITH ME"
                    : "MY DRIVE"}

              </p>

              <h1>

                {view === "trash"
                  ? "Trash"
                  : view === "shared"
                    ? "Shared with me"
                    : currentFolderObject
                      ? currentFolderObject.name
                      : "My Files"}

              </h1>

            </div>


            {view === "drive" && (

              <div className="header-actions">

                <label className="upload-button">

                  ⬆ Upload

                  <input
                    type="file"
                    hidden
                    onChange={
                      uploadFile
                    }
                  />

                </label>


                <button
                  onClick={() =>
                    setShowFolderInput(
                      true
                    )
                  }
                >
                  + New Folder
                </button>

              </div>

            )}

          </div>


          {/* ==================================================
              BREADCRUMB
          ================================================== */}

          {view === "drive" &&
            currentFolder !== null && (

              <div className="breadcrumb">

                <button
                  onClick={goToRoot}
                >
                  My Drive
                </button>

                <span>
                  /
                </span>

                <span>
                  {
                    currentFolderObject?.name
                  }
                </span>

              </div>

            )}


          {/* ==================================================
              SEARCH
          ================================================== */}

          {view === "drive" && (

            <div className="search-box">

              <span>
                🔍
              </span>

              <input
                placeholder="Search files..."
                value={search}
                onChange={(event) =>
                  setSearch(
                    event.target.value
                  )
                }
              />

            </div>

          )}


          {/* ==================================================
              NEW FOLDER
          ================================================== */}

          {view === "drive" &&
            showFolderInput && (

              <div className="new-folder">

                <input
                  autoFocus
                  value={folderName}
                  onChange={(event) =>
                    setFolderName(
                      event.target.value
                    )
                  }
                  placeholder="Folder name"
                  onKeyDown={(event) => {
                    if (
                      event.key ===
                      "Enter"
                    ) {
                      createFolder();
                    }
                  }}
                />

                <button
                  onClick={
                    createFolder
                  }
                >
                  Create
                </button>

                <button
                  className="secondary"
                  onClick={() => {
                    setShowFolderInput(
                      false
                    );

                    setFolderName("");
                  }}
                >
                  Cancel
                </button>

              </div>

            )}


          {/* ==================================================
              MESSAGE
          ================================================== */}

          {message && (

            <div className="notification">

              <span>
                {message}
              </span>

              <button
                className="close-message"
                onClick={() =>
                  setMessage("")
                }
              >
                ×
              </button>

            </div>

          )}


          {/* ==================================================
              SHARED VIEW
          ================================================== */}

          {view === "shared" && (

            <div className="file-card">

              <div className="table-header shared-header">

                <span>
                  Name
                </span>

                <span>
                  Owner
                </span>

                <span>
                  Permission
                </span>

                <span>
                  Actions
                </span>

              </div>


              {sharedFiles.map(
                (file) => (

                  <div
                    className="file-row shared-row"
                    key={
                      file.share_id
                    }
                  >

                    <span className="file-name">

                      {getFileIcon(
                        file.content_type
                      )}

                      {" "}

                      {file.name}

                    </span>


                    <span>
                      {file.owner_name}
                    </span>


                    <span>

                      <span
                        className={
                          file.permission ===
                          "EDITOR"
                            ? "permission editor"
                            : "permission viewer"
                        }
                      >
                        {file.permission}
                      </span>

                    </span>


                    <span>

                      <button
                        className="small-button"
                        onClick={() =>
                          downloadSharedFile(
                            file
                          )
                        }
                      >
                        Download
                      </button>

                    </span>

                  </div>

                )
              )}


              {!loading &&
                sharedFiles.length ===
                  0 && (

                  <div className="empty">

                    <div className="empty-icon">
                      ⭐
                    </div>

                    <h3>
                      Nothing shared with you
                    </h3>

                    <p>
                      Files shared with your
                      account will appear here.
                    </p>

                  </div>

                )}

            </div>

          )}


          {/* ==================================================
              DRIVE / TRASH
          ================================================== */}

          {view !== "shared" && (

            <div className="file-card">

              <div className="table-header">

                <span>
                  Name
                </span>

                <span>
                  Type
                </span>

                <span>
                  Size
                </span>

                <span>
                  Actions
                </span>

              </div>


              {/* FOLDERS */}

              {view === "drive" &&
                visibleFolders.map(
                  (folder) => (

                    <div
                      className="file-row"
                      key={
                        `folder-${folder.id}`
                      }
                    >

                      <span
                        className="file-name folder-name"
                        onDoubleClick={() =>
                          openFolder(
                            folder.id
                          )
                        }
                      >
                        📁{" "}
                        {folder.name}
                      </span>

                      <span>
                        Folder
                      </span>

                      <span>
                        —
                      </span>

                      <span>

                        <button
                          className="small-button"
                          onClick={() =>
                            openFolder(
                              folder.id
                            )
                          }
                        >
                          Open
                        </button>

                      </span>

                    </div>

                  )
                )}


              {/* FILES */}

              {files.map(
                (file) => (

                  <div
                    className="file-row"
                    key={file.id}
                  >

                    <span className="file-name">

                      {getFileIcon(
                        file.content_type
                      )}

                      {" "}

                      {file.name}

                    </span>


                    <span>
                      {getFileType(
                        file.content_type
                      )}
                    </span>


                    <span>
                      {formatSize(
                        file.size
                      )}
                    </span>


                    <span className="row-actions">

                      {view ===
                      "drive" ? (
                        <>

                          <button
                            className="small-button"
                            onClick={() =>
                              downloadFile(
                                file
                              )
                            }
                          >
                            Download
                          </button>


                          <button
                            className="version-button"
                            onClick={() =>
                              openVersionHistory(
                                file
                              )
                            }
                          >
                            Versions
                          </button>


                          <button
                            className="share-button"
                            onClick={() =>
                              openShareModal(
                                file
                              )
                            }
                          >
                            Share
                          </button>


                          <button
                            className="danger-button"
                            onClick={() =>
                              deleteFile(
                                file.id
                              )
                            }
                          >
                            Delete
                          </button>

                        </>
                      ) : (

                        <>

                          <button
                            className="small-button"
                            onClick={() =>
                              restoreFile(
                                file.id
                              )
                            }
                          >
                            Restore
                          </button>


                          <button
                            className="danger-button"
                            onClick={() =>
                              permanentlyDeleteFile(
                                file.id
                              )
                            }
                          >
                            Delete Forever
                          </button>

                        </>

                      )}

                    </span>

                  </div>

                )
              )}


              {/* EMPTY */}

              {!loading &&
                files.length ===
                  0 &&
                visibleFolders.length ===
                  0 && (

                  <div className="empty">

                    <div className="empty-icon">

                      {view ===
                      "trash"
                        ? "🗑"
                        : "☁"}

                    </div>

                    <h3>

                      {view ===
                      "trash"
                        ? "Trash is empty"
                        : search
                          ? "No matching files"
                          : "No files yet"}

                    </h3>

                    <p>

                      {view ===
                      "trash"
                        ? "Deleted files will appear here."
                        : search
                          ? "Try another search term."
                          : "Upload your first file to get started."}

                    </p>

                  </div>

                )}


              {loading && (

                <div className="empty">

                  <div className="empty-icon">
                    ⏳
                  </div>

                  <p>
                    Loading...
                  </p>

                </div>

              )}

            </div>

          )}

        </main>

      </div>


      {/* ========================================================
          SHARE MODAL
      ======================================================== */}

      {showShareModal &&
        shareFile && (

        <div
          className="modal-overlay"
          onClick={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeShareModal();
            }
          }}
        >

          <div className="share-modal">

            <div className="modal-header">

              <div>

                <p className="eyebrow">
                  SHARE FILE
                </p>

                <h2>
                  Share {shareFile.name}
                </h2>

              </div>


              <button
                className="modal-close"
                onClick={
                  closeShareModal
                }
              >
                ×
              </button>

            </div>


            <label>
              User email
            </label>

            <input
              autoFocus
              value={shareEmail}
              onChange={(event) =>
                setShareEmail(
                  event.target.value
                )
              }
              placeholder="friend@example.com"
              onKeyDown={(event) => {
                if (
                  event.key ===
                  "Enter"
                ) {
                  submitShare();
                }
              }}
            />


            <label>
              Permission
            </label>

            <select
              value={
                sharePermission
              }
              onChange={(event) =>
                setSharePermission(
                  event.target
                    .value as
                    | "VIEWER"
                    | "EDITOR"
                )
              }
            >

              <option value="VIEWER">
                Viewer — Can download
              </option>

              <option value="EDITOR">
                Editor — Can modify
              </option>

            </select>


            <div className="permission-help">

              {sharePermission ===
              "VIEWER"
                ? "Viewers can access and download the file."
                : "Editors can access the file and perform editing operations."}

            </div>


            <div className="modal-actions">

              <button
                className="secondary"
                onClick={
                  closeShareModal
                }
              >
                Cancel
              </button>

              <button
                onClick={
                  submitShare
                }
                disabled={loading}
              >
                {loading
                  ? "Sharing..."
                  : "Share File"}
              </button>

            </div>

          </div>

        </div>

      )}


      {/* ========================================================
          VERSION HISTORY MODAL
      ======================================================== */}

      {showVersionModal &&
        versionFile && (

        <div
          className="modal-overlay"
          onClick={(event) => {
            if (
              event.target ===
              event.currentTarget
            ) {
              closeVersionHistory();
            }
          }}
        >

          <div className="share-modal version-modal">

            <div className="modal-header">

              <div>

                <p className="eyebrow">
                  VERSION HISTORY
                </p>

                <h2>
                  {versionFile.name}
                </h2>

              </div>


              <button
                className="modal-close"
                onClick={
                  closeVersionHistory
                }
              >
                ×
              </button>

            </div>


            {/* UPLOAD VERSION */}

            <label className="upload-version">

              ⬆ Upload New Version

              <input
                type="file"
                hidden
                onChange={
                  uploadNewVersion
                }
              />

            </label>


            {/* VERSION LIST */}

            <div className="version-list">

              {versions.map(
                (version) => (

                  <div
                    className="version-item"
                    key={version.id}
                  >

                    <div className="version-info">

                      <div className="version-title">

                        Version{" "}
                        {version.version_number}

                        {version.is_current && (
                          <span className="current-version">
                            Current
                          </span>
                        )}

                      </div>


                      <div className="version-meta">

                        {formatSize(
                          version.size
                        )}

                        {" • "}

                        {new Date(
                          version.created_at
                        ).toLocaleString()}

                      </div>

                    </div>


                    <div className="version-actions">

                      <button
                        className="small-button"
                        onClick={() =>
                          downloadVersion(
                            version
                          )
                        }
                      >
                        Download
                      </button>


                      {!version.is_current && (

                        <button
                          className="version-button"
                          onClick={() =>
                            restoreVersion(
                              version
                            )
                          }
                        >
                          Restore
                        </button>

                      )}

                    </div>

                  </div>

                )
              )}


              {versions.length === 0 &&
                !loading && (

                  <div className="empty version-empty">

                    <div className="empty-icon">
                      🕘
                    </div>

                    <p>
                      No versions yet.
                    </p>

                    <span>
                      Upload a new version to
                      start version history.
                    </span>

                  </div>

                )}

            </div>


            <div className="modal-actions">

              <button
                className="secondary"
                onClick={
                  closeVersionHistory
                }
              >
                Close
              </button>

            </div>

          </div>

        </div>

      )}

    </div>
  );
}


// ============================================================
// FILE SIZE
// ============================================================

function formatSize(
  bytes: number
): string {

  if (bytes === 0) {
    return "0 Bytes";
  }

  const units = [
    "Bytes",
    "KB",
    "MB",
    "GB",
    "TB",
  ];

  const index =
    Math.floor(
      Math.log(bytes) /
        Math.log(1024)
    );

  return (
    parseFloat(
      (
        bytes /
        Math.pow(
          1024,
          index
        )
      ).toFixed(2)
    ) +
    " " +
    units[index]
  );
}


// ============================================================
// FILE TYPE
// ============================================================

function getFileType(
  contentType: string
): string {

  if (!contentType) {
    return "FILE";
  }

  const parts =
    contentType.split("/");

  if (parts.length < 2) {
    return contentType.toUpperCase();
  }

  return parts[1].toUpperCase();
}


// ============================================================
// FILE ICON
// ============================================================

function getFileIcon(
  contentType: string
): string {

  if (
    contentType.startsWith(
      "image/"
    )
  ) {
    return "🖼️";
  }

  if (
    contentType.startsWith(
      "video/"
    )
  ) {
    return "🎥";
  }

  if (
    contentType.startsWith(
      "audio/"
    )
  ) {
    return "🎵";
  }

  if (
    contentType.includes("pdf")
  ) {
    return "📕";
  }

  if (
    contentType.includes("zip") ||
    contentType.includes(
      "compressed"
    )
  ) {
    return "🗜️";
  }

  if (
    contentType.includes("word") ||
    contentType.includes(
      "document"
    )
  ) {
    return "📘";
  }

  if (
    contentType.includes(
      "spreadsheet"
    ) ||
    contentType.includes(
      "excel"
    )
  ) {
    return "📗";
  }

  if (
    contentType.includes("text")
  ) {
    return "📝";
  }

  return "📄";
}
