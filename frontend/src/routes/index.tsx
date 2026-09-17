import type { QuestDetail, QuestListItem, QuestStatus } from '#/shared/api/game';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createFileRoute } from '@tanstack/react-router';
import { useMemo, useState } from 'react';
import { useTraderSelection } from '#/providers/TraderSelectionProvider';
import { getQuest, getQuests, startQuest } from '#/shared/api/game';

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

  const questsQuery = useQuery({
    queryKey: ['quests', selectedTraderSlug],
    queryFn:  () => getQuests({ trader: selectedTraderSlug }),
  });

  const visibleQuests = useMemo(() => {
    return filterQuests(questsQuery.data ?? [], showCompleted, showLocked);
  }, [questsQuery.data, showCompleted, showLocked]);
  const selectedQuest = visibleQuests.find(quest => quest.id === selectedQuestId) ?? visibleQuests[0] ?? null;

  const questDetailQuery = useQuery({
    queryKey: ['quest', selectedQuest?.id],
    queryFn:  () => getQuest(selectedQuest?.id ?? 0),
    enabled:  Boolean(selectedQuest),
  });

  const detail = questDetailQuery.data ?? selectedQuest;
  const groupedQuests = useMemo(() => groupQuestsByLoyalty(visibleQuests), [visibleQuests]);

  const startQuestMutation = useMutation({
    mutationFn: startQuest,
    onSuccess:  (quest) => {
      setSelectedQuestId(quest.id);
      void queryClient.invalidateQueries({ queryKey: ['quests'] });
      void queryClient.invalidateQueries({ queryKey: ['quest', quest.id] });
    },
  });

  function handleStartQuest() {
    if (!selectedQuest || selectedQuest.status !== 'available') {
      return;
    }

    startQuestMutation.mutate(selectedQuest.id);
  }

  return (
    <div className={classes.root}>
      <section className={classes.questWindow}>
        <header className={classes.questHeader}>
          <button
            className={classes.completeButton}
            disabled={selectedQuest?.status !== 'active'}
            type="button"
          >
            ЗАВЕРШИТЬ
          </button>

          <div className={classes.questTitle}>
            <span className={classes.questTitleIcon}>{getQuestIcon(selectedQuest)}</span>
            <span>{detail?.title ?? getEmptyTitle(questsQuery.isLoading, questsQuery.isError)}</span>
          </div>

          <div className={classes.questMeta}>
            <span>Любая локация</span>
            <strong>{getStatusLabel(detail?.status)}</strong>
            <span className={classes.loyaltyBadge}>{getQuestLevel(detail)}</span>
          </div>
        </header>

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
                  type="button"
                >
                  ▦
                </button>

                <button
                  aria-label="Сетка"
                  type="button"
                >
                  ▦
                </button>
              </div>
            </div>

            <div className={classes.questList}>
              {groupedQuests.map(group => (
                <section
                  key={group.level}
                  className={classes.questGroup}
                >
                  <button
                    className={classes.groupTitle}
                    type="button"
                  >
                    <span className={classes.loyaltyBadge}>{group.level}</span>
                    <span>{`УРОВЕНЬ ЛОЯЛЬНОСТИ ${group.level}`}</span>
                    <span>⌃</span>
                  </button>

                  {group.quests.map(quest => (
                    <button
                      key={quest.id}
                      className={`${classes.questRow} ${quest.id === selectedQuest?.id ? classes.questRowActive : ''}`}
                      type="button"
                      onClick={() => {
                        setSelectedQuestId(quest.id);
                      }}
                    >
                      <span className={classes.rowIcon}>{getQuestIcon(quest)}</span>
                      <span className={classes.rowTitle}>{quest.title}</span>
                      <span className={classes.rowStatus}>{getStatusLabel(quest.status)}</span>
                      <span className={classes.rowArrow}>›</span>
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
                    isPending={startQuestMutation.isPending}
                    quest={detail}
                    onStart={handleStartQuest}
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
  quest:     QuestListItem | QuestDetail;
  isPending: boolean;
  onStart:   () => void;
}

function QuestDetails({
  quest,
  isPending,
  onStart,
}: QuestDetailsProps) {
  const objectives = 'objectives' in quest ? quest.objectives : [];
  const requirements = 'requirements' in quest ? quest.requirements : [];
  const canStart = quest.status === 'available';

  return (
    <>
      <div className={classes.detailIntro}>
        <div className={classes.questImage}>
          <span>{quest.trader.name}</span>
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

          {canStart && (
            <button
              className={classes.startButton}
              disabled={isPending}
              type="button"
              onClick={onStart}
            >
              {isPending ? 'АКТИВАЦИЯ...' : 'НАЧАТЬ ЗАДАНИЕ'}
            </button>
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
                <span>{getObjectiveIcon(objective.type)}</span>
                <strong>{objective.title}</strong>
                <em>
                  {objective.current_amount}
                  {' / '}
                  {objective.required_amount}
                </em>
                {objective.completed && <span className={classes.doneMark}>✓</span>}
              </div>
            ))
          : (
              <div className={classes.objectiveRow}>
                <span>✦</span>
                <strong>Цели появятся после синхронизации</strong>
              </div>
            )}
      </section>

      <section className={classes.rewards}>
        <h2>Награды</h2>

        <div className={classes.rewardGrid}>
          <div className={classes.rewardItem}>
            <span>EXP</span>
            <strong>+10 000</strong>
          </div>

          <div className={classes.rewardItem}>
            <span>♟</span>
            <strong>
              {quest.trader.name}
              {' '}
              +0.25
            </strong>
          </div>

          <div className={classes.rewardItem}>
            <span>₽</span>
            <strong>Рубли</strong>
          </div>
        </div>
      </section>
    </>
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
    return '✦';
  }

  if (quest.status === 'completed') {
    return '✓';
  }

  if (quest.status === 'locked') {
    return '■';
  }

  return '✋';
}

function getObjectiveIcon(type: string) {
  switch (type) {
    case 'find_item':
    case 'handover_item':
      return '✋';
    case 'visit_location':
      return '⚑';
    case 'enter_code':
      return '#';
    case 'scan_qr':
      return '▣';
    default:
      return '✦';
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
