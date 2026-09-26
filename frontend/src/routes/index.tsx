import type { QuestDetail, QuestListItem, QuestObjective, QuestStatus } from '#/shared/api/game';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createFileRoute } from '@tanstack/react-router';
import { Banknote, ChartNoAxesColumnIncreasing, Check, ChevronRight, ChevronUp, Hand, Hash, LayoutGrid, List, LockKeyhole, MapPin, QrCode } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTraderSelection } from '#/providers/TraderSelectionProvider';
import { completeQuest, getQuest, getQuests, startQuest, submitObjective } from '#/shared/api/game';

import classes from './index.module.css';

export const Route = createFileRoute('/')({
  component: HomePage,
});

const DEFAULT_VISIBLE_STATUSES: QuestStatus[] = ['active', 'available'];

function HomePage() {
  const queryClient = useQueryClient();
  const { selectedTraderSlug } = useTraderSelection();
  const [selectedQuestId, setSelectedQuestId] = useState<number | null>(null);
  const [showCompleted, setShowCompleted] = useState(false);
  const [showLocked, setShowLocked] = useState(false);
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list');
  const [collapsedGroups, setCollapsedGroups] = useState<number[]>([]);

  const questsQuery = useQuery({
    queryKey:        ['quests', selectedTraderSlug],
    queryFn:         () => getQuests({ trader: selectedTraderSlug }),
    refetchInterval: 5000,
  });

  const visibleQuests = useMemo(() => {
    return filterQuests(questsQuery.data ?? [], showCompleted, showLocked);
  }, [questsQuery.data, showCompleted, showLocked]);
  const selectedQuest = (questsQuery.data ?? []).find(quest => quest.id === selectedQuestId) ?? visibleQuests[0] ?? null;

  const questDetailQuery = useQuery({
    queryKey:        ['quest', selectedQuest?.id],
    queryFn:         () => getQuest(selectedQuest?.id ?? 0),
    enabled:         Boolean(selectedQuest),
    refetchInterval: 3000,
  });

  const detail = questDetailQuery.data ?? selectedQuest;
  const groupedQuests = useMemo(() => groupQuestsByLoyalty(visibleQuests), [visibleQuests]);

  const startQuestMutation = useMutation({
    mutationFn: startQuest,
    onSuccess:  (quest) => {
      setSelectedQuestId(quest.id);
      queryClient.setQueryData(['quest', quest.id], quest);
      void queryClient.invalidateQueries({ queryKey: ['progress'] });
      void queryClient.invalidateQueries({ queryKey: ['quests'] });
      void queryClient.invalidateQueries({ queryKey: ['quest', quest.id] });
    },
  });

  function handleStartQuest() {
    if (!detail || detail.status !== 'available') {
      return;
    }

    startQuestMutation.mutate(detail.id);
  }

  const canComplete = detail?.status === 'active'
    && detail.progress.total > 0
    && detail.progress.completed === detail.progress.total;
  const completeQuestMutation = useMutation({
    mutationFn: completeQuest,
    onSuccess:  (quest) => {
      setSelectedQuestId(quest.id);
      setShowCompleted(true);
      queryClient.setQueryData(['quest', quest.id], quest);
    },
    onSettled: async (_data, _error, questId) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['quests'] }),
        queryClient.invalidateQueries({ queryKey: ['quest', questId] }),
        queryClient.invalidateQueries({ queryKey: ['progress'] }),
      ]);
    },
  });

  return (
    <div className={classes.root}>
      <section className={classes.questWindow}>
        <header className={classes.questHeader}>
          <button
            className={classes.completeButton}
            disabled={startQuestMutation.isPending || completeQuestMutation.isPending || !(detail?.status === 'available' || canComplete)}
            type="button"
            onClick={() => {
              if (detail?.status === 'available') {
                handleStartQuest();
              }
              else if (detail && canComplete) {
                completeQuestMutation.mutate(detail.id);
              }
            }}
          >
            {startQuestMutation.isPending ? 'ПРИНЯТИЕ...' : completeQuestMutation.isPending ? 'ЗАВЕРШЕНИЕ...' : detail?.status === 'available' || detail?.status === 'locked' ? 'ПРИНЯТЬ' : 'ЗАВЕРШИТЬ'}
          </button>

          <div className={classes.questTitle}>
            <span className={classes.questTitleIcon}>{getQuestIcon(selectedQuest)}</span>
            <span>{detail?.title ?? getEmptyTitle(questsQuery.isLoading, questsQuery.isError)}</span>
          </div>

          <div className={classes.questMeta}>
            <span>Любая локация</span>
            <strong>{getStatusLabel(detail?.status)}</strong>
            <span className={classes.loyaltyBadge}>{['I', 'II', 'III', 'IV'][getQuestLevel(detail) - 1]}</span>
          </div>
        </header>
        {startQuestMutation.isError && startQuestMutation.variables === detail?.id && (
          <p className={classes.error} role="alert">Не удалось принять квест. Попробуйте ещё раз.</p>
        )}
        {completeQuestMutation.isError && completeQuestMutation.variables === detail?.id && (
          <p className={classes.error} role="alert">Не удалось завершить квест. Попробуйте ещё раз.</p>
        )}

        <div className={classes.content}>
          <aside className={classes.sidebar}>
            <div className={classes.filters}>
              <label>
                <input
                  checked={showCompleted}
                  type="checkbox"
                  onChange={(event) => {
                    setShowCompleted(event.target.checked);
                  }}
                />
                <span>Завершенные</span>
              </label>

              <label>
                <input
                  checked={showLocked}
                  type="checkbox"
                  onChange={(event) => {
                    setShowLocked(event.target.checked);
                  }}
                />
                <span>Заблокированные</span>
              </label>

              <div className={classes.viewButtons}>
                <button
                  aria-label="Список"
                  title="Список"
                  aria-pressed={viewMode === 'list'}
                  onClick={() => setViewMode('list')}
                  type="button"
                >
                  <List aria-hidden="true" />
                </button>

                <button
                  aria-label="Сетка"
                  title="Сетка"
                  aria-pressed={viewMode === 'grid'}
                  onClick={() => setViewMode('grid')}
                  type="button"
                >
                  <LayoutGrid aria-hidden="true" />
                </button>
              </div>
            </div>

            <div className={`${classes.questList} ${viewMode === 'grid' ? classes.questListGrid : ''}`}>
              {groupedQuests.map(group => (
                <section
                  key={group.level}
                  className={classes.questGroup}
                >
                  <button
                    className={classes.groupTitle}
                    aria-expanded={!collapsedGroups.includes(group.level)}
                    onClick={() => setCollapsedGroups(previous => previous.includes(group.level) ? previous.filter(level => level !== group.level) : [...previous, group.level])}
                    type="button"
                  >
                    <span className={classes.loyaltyBadge}>{['I', 'II', 'III', 'IV'][group.level - 1]}</span>
                    <span>{`УРОВЕНЬ ЛОЯЛЬНОСТИ ${group.level}`}</span>
                    <ChevronUp aria-hidden="true" />
                  </button>

                  {!collapsedGroups.includes(group.level) && group.quests.map(quest => (
                    <button
                      key={quest.id}
                      className={`${classes.questRow} ${quest.id === selectedQuest?.id ? classes.questRowActive : ''}`}
                      type="button"
                      aria-pressed={quest.id === selectedQuest?.id}
                      onClick={() => {
                        setSelectedQuestId(quest.id);
                      }}
                    >
                      <span className={classes.rowIcon}>{getQuestIcon(quest)}</span>
                      <span className={classes.rowTitle}>{quest.title}</span>
                      <span className={classes.rowStatus}>{getStatusLabel(quest.status)}</span>
                      <ChevronRight className={classes.rowArrow} aria-hidden="true" />
                    </button>
                  ))}
                </section>
              ))}

              {!visibleQuests.length && (
                <div className={classes.emptyList}>
                  {questsQuery.isError
                    ? 'Связь с сервером потеряна'
                    : 'Нет квестов для выбранного торговца'}
                </div>
              )}
            </div>
          </aside>

          <article className={classes.details}>
            {detail
              ? (
                  <QuestDetails
                    quest={detail}
                    onSelect={() => setSelectedQuestId(detail.id)}
                  />
                )
              : (
                  <div className={classes.emptyDetails}>
                    <h2>{getEmptyTitle(questsQuery.isLoading, questsQuery.isError)}</h2>
                    <p>
                      {questsQuery.isLoading
                        ? 'Получаем список заданий по защищенному каналу.'
                        : 'Выберите другого торговца или измените фильтры списка.'}
                    </p>
                  </div>
                )}
          </article>
        </div>
      </section>
    </div>
  );
}

interface QuestDetailsProps {
  onSelect: () => void;
  quest:    QuestListItem | QuestDetail;
}

function QuestDetails({
  quest,
  onSelect,
}: QuestDetailsProps) {
  const objectives = 'objectives' in quest ? quest.objectives : [];
  const requirements = 'requirements' in quest ? quest.requirements : [];

  return (
    <>
      <div className={classes.detailIntro}>
        <div className={classes.questImage}>
          {quest.image
            ? <img key={quest.image} src={quest.image} alt={quest.title} />
            : <span>{quest.trader.name}</span>}
        </div>

        <div className={classes.questText}>
          <p>
            {quest.description || 'Информация по заданию ожидает подтверждения от оператора.'}
          </p>

          {requirements.length > 0 && (
            <div className={classes.requirements}>
              <span>Требуется:</span>
              {requirements.map(requirement => (
                <strong key={requirement.id}>{requirement.title}</strong>
              ))}
            </div>
          )}

        </div>
      </div>

      <section className={classes.objectives}>
        <h2>Цель(-и)</h2>

        {objectives.length > 0
          ? objectives.map(objective => (
              <div
                key={objective.id}
                className={`${classes.objectiveRow} ${objective.completed ? classes.objectiveRowDone : ''}`}
              >
                <div className={classes.objectiveLabel}>
                  {getObjectiveIcon(objective.type)}
                  <strong>{objective.title}</strong>
                </div>
                {objective.required_amount > 1 && (
                  <em>
                    {objective.current_amount}
                    {' / '}
                    {objective.required_amount}
                  </em>
                )}
                <ObjectiveAction key={objective.id} objective={objective} quest={quest} onSelect={onSelect} />
              </div>
            ))
          : (
              <div className={classes.objectiveRow}>
                <strong>Цели появятся после синхронизации</strong>
              </div>
            )}
      </section>

      <section className={classes.rewards}>
        <h2>Награды</h2>

        <div className={classes.rewardGrid}>
          <div className={classes.rewardItem}>
            <span>EXP</span>
            <div>
              <small>ОПЫТ</small>
              <strong>+10 000</strong>
            </div>
          </div>

          <div className={classes.rewardItem}>
            <span><ChartNoAxesColumnIncreasing aria-hidden="true" /></span>
            <div>
              <small>{quest.trader.name}</small>
              <strong>+0,25</strong>
            </div>
          </div>

          <div className={classes.rewardItem}>
            <span><Banknote aria-hidden="true" /></span>
            <strong>Рубли</strong>
          </div>
        </div>
      </section>
    </>
  );
}

function ObjectiveAction({ objective, quest, onSelect }: { objective: QuestObjective; quest: QuestListItem; onSelect: () => void }) {
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState(1);
  const remaining = objective.required_amount - objective.current_amount;
  const mutation = useMutation({
    mutationFn: () => submitObjective(objective.id, { amount }),
    onMutate:   onSelect,
    onSuccess:  () => setAmount(1),
    onSettled:  async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['quest', quest.id] }),
        queryClient.invalidateQueries({ queryKey: ['quests'] }),
        queryClient.invalidateQueries({ queryKey: ['progress'] }),
      ]);
    },
  });
  const latest = objective.latest_submission;
  const waiting = latest?.status === 'pending' || mutation.isPending;

  if (objective.completed) {
    return <Check className={classes.doneMark} aria-label="Выполнено" />;
  }

  if (quest.status !== 'active') {
    return null;
  }

  return (
    <div className={classes.objectiveAction}>
      {remaining > 1 && !waiting && (
        <input
          aria-label={`Количество: ${objective.title}`}
          type="number"
          min={1}
          max={remaining}
          value={amount}
          onChange={event => setAmount(event.target.valueAsNumber)}
        />
      )}
      <button
        type="button"
        disabled={waiting || !Number.isInteger(amount) || amount < 1 || amount > remaining}
        onClick={() => mutation.mutate()}
      >
        {waiting ? 'Ожидание' : objective.type === 'handover_item' ? 'Передать' : 'На проверку'}
      </button>
      {latest?.status === 'rejected' && !waiting && (
        <small role="status">{latest.admin_comment || 'Заявка отклонена. Можно отправить повторно.'}</small>
      )}
      {mutation.isError && <small role="alert">Не удалось отправить заявку. Попробуйте ещё раз.</small>}
    </div>
  );
}

function filterQuests(quests: QuestListItem[], showCompleted: boolean, showLocked: boolean) {
  return quests.filter((quest) => {
    if (DEFAULT_VISIBLE_STATUSES.includes(quest.status)) {
      return true;
    }

    if (quest.status === 'completed') {
      return showCompleted;
    }

    if (quest.status === 'locked') {
      return showLocked;
    }

    return false;
  });
}

function groupQuestsByLoyalty(quests: QuestListItem[]) {
  const groups = new Map<number, QuestListItem[]>();

  quests.forEach((quest) => {
    const level = getQuestLevel(quest);
    groups.set(level, [...(groups.get(level) ?? []), quest]);
  });

  return Array.from(groups.entries())
    .sort(([levelA], [levelB]) => levelA - levelB)
    .map(([level, groupQuests]) => ({
      level,
      quests: groupQuests,
    }));
}

function getQuestLevel(quest: QuestListItem | null | undefined) {
  if (!quest) {
    return 1;
  }

  return Math.min(Math.floor(quest.sort_order / 5) + 1, 4);
}

function getQuestIcon(quest: QuestListItem | null | undefined) {
  if (!quest) {
    return <Hand aria-hidden="true" />;
  }

  if (quest.status === 'completed') {
    return <Check aria-hidden="true" />;
  }

  if (quest.status === 'locked') {
    return <LockKeyhole aria-hidden="true" />;
  }

  return <Hand aria-hidden="true" />;
}

function getObjectiveIcon(type: string) {
  switch (type) {
    case 'find_item':
    case 'handover_item':
      return <Hand aria-hidden="true" />;
    case 'visit_location':
      return <MapPin aria-hidden="true" />;
    case 'enter_code':
      return <Hash aria-hidden="true" />;
    case 'scan_qr':
      return <QrCode aria-hidden="true" />;
    default:
      return <Hand aria-hidden="true" />;
  }
}

function getStatusLabel(status: QuestStatus | undefined) {
  switch (status) {
    case 'active':
      return 'активно!';
    case 'available':
      return 'доступно';
    case 'completed':
      return 'завершено';
    case 'locked':
      return 'закрыто';
    default:
      return '';
  }
}

function getEmptyTitle(isLoading: boolean, isError: boolean) {
  if (isError) {
    return 'СВЯЗЬ ПОТЕРЯНА';
  }

  return isLoading ? 'ЗАГРУЗКА ЗАДАНИЙ' : 'ЗАДАНИЙ НЕТ';
}
