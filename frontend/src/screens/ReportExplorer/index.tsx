/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Box, IconButton, Typography } from '@mui/material';

import type { CatalogItem, CatalogNode } from '@/components/browse/types';
import { useGlobal } from '@/contexts/GlobalContext';
import {
  getBreadcrumbs,
  getCatalogItemById,
  getChildCatalogNodes,
  getChildCatalogNodesByType,
  getRootCatalogNodes,
} from '@/services/catalog.service';

import ExplorerHeader from './ExplorerHeader';
import FolderGrid from './FolderGrid';
import ReportGrid from './ReportGrid';
import ReportViewer from './ReportViewer';
import SkillPreviewModal from './SkillPreviewModal';

const REPORT_ITEM_TYPES = [
  'html_report',
  'powerbi_report',
  'looker_report',
  'looker_studio_report',
  'quicksight_report',
  'tableau_report',
];

interface ProjectSection {
  project: CatalogItem;
  assetFolder: CatalogItem;
  folders: CatalogItem[];
  reports: CatalogItem[];
}

interface ReportExplorerProps {
  initialLaui?: string;
  initialReportLaui?: string;
  onFolderChange: (laui: string | null, path?: string) => void;
  onReportChange: (laui: string | null) => void;
}

export default function ReportExplorer({
  initialLaui,
  initialReportLaui,
  onFolderChange,
  onReportChange,
}: ReportExplorerProps) {
  const { setAccountLaui } = useGlobal();
  const [folderPath, setFolderPath] = useState<CatalogItem[]>([]);
  const [currentFolder, setCurrentFolder] = useState<CatalogItem | null>(null);
  const [folders, setFolders] = useState<CatalogItem[]>([]);
  const [reports, setReports] = useState<CatalogItem[]>([]);
  const [selectedReport, setSelectedReport] = useState<CatalogItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [projectSections, setProjectSections] = useState<ProjectSection[]>([]);
  const [isAtHome, setIsAtHome] = useState(true);
  const [previewSkillLaui, setPreviewSkillLaui] = useState<string | null>(null);

  const assetRootRef = useRef<CatalogItem | null>(null);
  const projectPairsRef = useRef<Map<string, { project: CatalogItem; assetFolder: CatalogItem }>>(
    new Map(),
  );

  const loadFolderContents = useCallback(async (folder: CatalogItem) => {
    setLoading(true);
    setSelectedReport(null);
    setError('');
    try {
      const perm = folder.permission ?? 'view';
      const [subfolderRes, ...reportResults] = await Promise.all([
        getChildCatalogNodesByType(folder.laui, 'folder.asset', perm, false, 1, 100),
        ...REPORT_ITEM_TYPES.map((t) =>
          getChildCatalogNodesByType(folder.laui, t, perm, false, 1, 100),
        ),
      ]);
      setFolders(subfolderRes.items.map((n: CatalogNode) => n.item));
      setReports(reportResults.flatMap((r) => r.items.map((n: CatalogNode) => n.item)));
    } catch {
      setError('Failed to load folder contents.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadProjectSections = useCallback(async (): Promise<ProjectSection[]> => {
    const root = await getRootCatalogNodes();
    const account = root.items[0];
    if (!account) return [];
    if (account.item.item_type === 'folder.account') {
      setAccountLaui(account.item.laui);
      if (localStorage.getItem('la_account_laui') !== account.item.laui)
        localStorage.setItem('la_account_laui', account.item.laui);
    }
    const projects = account.children
      .map((n: CatalogNode) => n.item)
      .filter((i: CatalogItem) => i.item_type === 'folder.project');

    const sections = await Promise.all(
      projects.map(async (proj: CatalogItem) => {
        const assetRes = await getChildCatalogNodes(
          proj.laui,
          proj.permission ?? 'view',
          false,
          1,
          10,
          'folder',
        );
        const assetFolder = assetRes.items
          .map((n: CatalogNode) => n.item)
          .find((i: CatalogItem) => i.item_type === 'folder.asset');
        if (!assetFolder) return null;
        projectPairsRef.current.set(proj.laui, { project: proj, assetFolder });
        const perm = assetFolder.permission ?? 'view';
        const [subfolderRes, ...reportResults] = await Promise.all([
          getChildCatalogNodesByType(assetFolder.laui, 'folder.asset', perm, false, 1, 100),
          ...REPORT_ITEM_TYPES.map((t) =>
            getChildCatalogNodesByType(assetFolder.laui, t, perm, false, 1, 100),
          ),
        ]);
        return {
          project: proj,
          assetFolder,
          folders: subfolderRes.items.map((n: CatalogNode) => n.item),
          reports: reportResults.flatMap((r) => r.items.map((n: CatalogNode) => n.item)),
        } as ProjectSection;
      }),
    );
    return sections.filter(Boolean) as ProjectSection[];
  }, [setAccountLaui]);

  useEffect(() => {
    const flatten = (nodes: CatalogNode[]): CatalogItem[] => {
      const result: CatalogItem[] = [];
      const walk = (node: CatalogNode) => {
        if (node.parents?.length) node.parents.forEach(walk);
        result.push(node.item);
      };
      nodes.forEach(walk);
      return result;
    };

    const restoreFolder = async (folderLaui: string) => {
      const targetItem = (await getCatalogItemById(folderLaui)) as CatalogItem;
      const breadcrumbRes = await getBreadcrumbs(folderLaui);
      const ancestorItems = flatten(breadcrumbRes.items ?? []);
      const projectItem = ancestorItems.find((i) => i.item_type === 'folder.project');
      const pair = projectItem ? projectPairsRef.current.get(projectItem.laui) : null;
      if (!pair) {
        setIsAtHome(true);
        setLoading(false);
        return;
      }

      assetRootRef.current = pair.assetFolder;
      const assetIdx = ancestorItems.findIndex((i) => i.laui === pair.assetFolder.laui);
      const subPath =
        assetIdx >= 0
          ? ancestorItems.slice(assetIdx + 1).filter((i) => i.laui !== targetItem.laui)
          : [];
      setFolderPath([pair.project, ...subPath]);
      setCurrentFolder(targetItem);
      setIsAtHome(false);
      await loadFolderContents(targetItem);
    };

    const init = async () => {
      setLoading(true);
      setError('');
      try {
        const sections = await loadProjectSections();
        if (!sections.length) {
          setError('No projects found.');
          setLoading(false);
          return;
        }
        setProjectSections(sections);

        if (initialLaui) {
          await restoreFolder(initialLaui);
          if (initialReportLaui) {
            const reportItem = (await getCatalogItemById(initialReportLaui)) as CatalogItem;
            setSelectedReport(reportItem);
          }
        } else if (initialReportLaui) {
          const reportItem = (await getCatalogItemById(initialReportLaui)) as any;
          if (reportItem.parent_laui) {
            await restoreFolder(reportItem.parent_laui);
          } else {
            setIsAtHome(true);
            setLoading(false);
          }
          setSelectedReport(reportItem as CatalogItem);
        } else {
          setIsAtHome(true);
          setCurrentFolder(null);
          setLoading(false);
        }
      } catch {
        setError('Failed to initialise Report Explorer.');
        setLoading(false);
      }
    };
    void init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleOpenFolder = async (folder: CatalogItem, projectForRoot?: CatalogItem) => {
    if (isAtHome && projectForRoot) {
      const pair = projectPairsRef.current.get(projectForRoot.laui);
      if (!pair) return;
      assetRootRef.current = pair.assetFolder;
      setFolderPath([pair.project]);
      setCurrentFolder(folder);
      setIsAtHome(false);
      onFolderChange(folder.laui, `${pair.project.name}/${folder.name}`);
      await loadFolderContents(folder);
      return;
    }
    const assetRoot = assetRootRef.current;
    let newFolderPath = folderPath;
    if (currentFolder && assetRoot && currentFolder.laui !== assetRoot.laui) {
      newFolderPath = [...folderPath, currentFolder];
      setFolderPath(newFolderPath);
    }
    setCurrentFolder(folder);
    const path = [...newFolderPath, folder].map((i) => i.name).join('/');
    onFolderChange(folder.laui, path);
    await loadFolderContents(folder);
  };

  const handleNavigateTo = async (item: CatalogItem | null, index: number) => {
    if (item === null) {
      assetRootRef.current = null;
      setFolderPath([]);
      setCurrentFolder(null);
      setIsAtHome(true);
      setSelectedReport(null);
      onFolderChange(null);
      return;
    }
    if (item.item_type === 'folder.project') {
      const pair = projectPairsRef.current.get(item.laui);
      if (!pair) return;
      assetRootRef.current = pair.assetFolder;
      setFolderPath([pair.project]);
      setCurrentFolder(pair.assetFolder);
      setIsAtHome(false);
      onFolderChange(pair.assetFolder.laui, pair.project.name);
      await loadFolderContents(pair.assetFolder);
      return;
    }
    const newPath = folderPath.slice(0, index);
    setFolderPath(newPath);
    setCurrentFolder(item);
    const path = [...newPath, item].map((i) => i.name).join('/');
    onFolderChange(item.laui, path);
    await loadFolderContents(item);
  };

  // Build and dispatch the current skill context to ChatPanel
  const dispatchSkillContext = useCallback(() => {
    let skillLauis: string[];

    if (selectedReport) {
      const reportSkill = (selectedReport as any)?.skill_laui as string | undefined;
      if (reportSkill) {
        // Report has its own skill — wins over all folder/project skills
        skillLauis = [reportSkill];
      } else if (isAtHome) {
        // Report opened from home, no own skill — inherit from its project's asset folder only
        const section = projectSections.find((s) => s.project.laui === selectedReport.project_laui);
        skillLauis = [section?.assetFolder.skill_laui].filter((v): v is string => Boolean(v));
      } else {
        // Report opened from folder, no own skill — inherit from folder hierarchy
        const candidates = [
          currentFolder?.skill_laui,
          assetRootRef.current?.skill_laui,
          ...folderPath.map((f) => f.skill_laui),
        ];
        skillLauis = candidates
          .filter((v): v is string => Boolean(v))
          .filter((v, i, arr) => arr.indexOf(v) === i);
      }
    } else if (isAtHome) {
      // No report open, on home — show all project asset folder skills
      skillLauis = projectSections
        .map((s) => s.assetFolder.skill_laui)
        .filter((v): v is string => Boolean(v));
    } else {
      // No report open, in a folder — inherit from folder hierarchy
      const candidates = [
        currentFolder?.skill_laui,
        assetRootRef.current?.skill_laui,
        ...folderPath.map((f) => f.skill_laui),
      ];
      skillLauis = candidates
        .filter((v): v is string => Boolean(v))
        .filter((v, i, arr) => arr.indexOf(v) === i);
    }

    window.dispatchEvent(new CustomEvent('la:report-skill', { detail: { skillLauis } }));
  }, [selectedReport, currentFolder, folderPath, isAtHome, projectSections]);

  // Re-dispatch whenever navigation or report selection changes
  useEffect(() => {
    dispatchSkillContext();
  }, [dispatchSkillContext]);

  // Re-dispatch when ChatPanel mounts late (e.g. user opens chat after page loads)
  useEffect(() => {
    window.addEventListener('la:chatpanel-ready', dispatchSkillContext);
    return () => window.removeEventListener('la:chatpanel-ready', dispatchSkillContext);
  }, [dispatchSkillContext]);

  const assetRootLaui = assetRootRef.current?.laui;
  const displayPath = isAtHome
    ? []
    : currentFolder?.laui === assetRootLaui
      ? folderPath
      : ([...folderPath, currentFolder].filter(Boolean) as CatalogItem[]);

  return (
    <Box
      sx={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'var(--bg-primary)',
      }}
    >
      <ExplorerHeader
        folderPath={displayPath}
        onNavigateTo={(item, index) => void handleNavigateTo(item, index)}
      />

      {error ? (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            flex: 1,
          }}
        >
          <Typography sx={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            {error}
          </Typography>
        </Box>
      ) : selectedReport ? (
        <ReportViewer
          report={selectedReport}
          currentFolder={currentFolder}
          onBack={() => {
            setSelectedReport(null);
            onReportChange(null);
          }}
        />
      ) : isAtHome ? (
        <Box sx={{ flex: 1, overflow: 'auto', px: 1 }}>
          {loading ? (
            <FolderGrid folders={[]} loading onOpen={() => {}} />
          ) : (
            projectSections.map((section) => (
              <Box key={section.project.laui} sx={{ mb: 3 }}>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    px: 2,
                    py: 1,
                    gap: 0.5,
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: 'var(--text-secondary)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                    }}
                  >
                    {section.project.name}
                  </Typography>
                  {section.assetFolder.skill_laui && (
                    <IconButton
                      size="small"
                      onClick={() => setPreviewSkillLaui(section.assetFolder.skill_laui!)}
                      sx={{
                        color: 'var(--text-secondary)',
                        opacity: 0.5,
                        p: 0.25,
                        '&:hover': {
                          opacity: 1,
                          color: 'var(--accent, #7c3aed)',
                          bgcolor: 'transparent',
                        },
                      }}
                    >
                      <InfoOutlinedIcon sx={{ fontSize: 14 }} />
                    </IconButton>
                  )}
                </Box>
                <FolderGrid
                  folders={section.folders}
                  loading={false}
                  onOpen={(f) => void handleOpenFolder(f, section.project)}
                />
                {section.reports.length > 0 && (
                  <ReportGrid
                    reports={section.reports}
                    loading={false}
                    onOpen={(r) => {
                      setSelectedReport(r);
                      onReportChange(r.laui);
                    }}
                  />
                )}
                {section.folders.length === 0 && section.reports.length === 0 && (
                  <Typography
                    sx={{
                      px: 2,
                      pb: 1,
                      fontSize: '0.8rem',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    No reports yet
                  </Typography>
                )}
              </Box>
            ))
          )}
        </Box>
      ) : (
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          <FolderGrid
            folders={folders}
            loading={loading && folders.length === 0 && reports.length === 0}
            onOpen={(folder) => void handleOpenFolder(folder)}
          />
          {!loading && reports.length > 0 && (
            <>
              {folders.length > 0 && (
                <Box sx={{ px: 3, pb: 0.5 }}>
                  <Typography
                    sx={{
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      color: 'var(--text-secondary)',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                    }}
                  >
                    Reports
                  </Typography>
                </Box>
              )}
              <ReportGrid
                reports={reports}
                loading={false}
                onOpen={(r) => {
                  setSelectedReport(r);
                  onReportChange(r.laui);
                }}
              />
            </>
          )}
        </Box>
      )}

      <SkillPreviewModal
        open={Boolean(previewSkillLaui)}
        onClose={() => setPreviewSkillLaui(null)}
        skillLaui={previewSkillLaui}
      />
    </Box>
  );
}
