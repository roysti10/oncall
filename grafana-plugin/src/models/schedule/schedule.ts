import { SelectOptions } from '@grafana/ui';
import dayjs from 'dayjs';
import { omit, reject } from 'lodash-es';
import { action, observable, toJS } from 'mobx';
import ReactCSSTransitionGroup from 'react-transition-group'; // ES6

import BaseStore from 'models/base_store';
import { Timezone } from 'models/timezone/timezone.types';
import { makeRequest } from 'network';
import { RootStore } from 'state';
import { SelectOption } from 'state/types';

import { fillGaps } from './schedule.helpers';
import { Events, Rotation, RotationType, Schedule, ScheduleEvent } from './schedule.types';

const DEFAULT_FORMAT = 'YYYY-MM-DDTHH:mm:ss';

let I = 0;

function getUsers() {
  const rnd = Math.random();
  /*

        if (rnd > 0.66) {
          return [];
        }
*/

  const users = [
    'U5WE86241LNEA',
    'U9XM1G7KTE3KW',
    'UYKS64M6C59XM',
    'UFFIRDUFXA6W3',
    'UPRMSTP9LCADE',
    'UR6TVJWZYV19M',
    'UHRMQQ7KETPCS',
  ];

  /* if (rnd > 0.33) {
          return [users[Math.floor(Math.random() * users.length)], users[Math.floor(Math.random() * users.length)]];
        }*/

  return ['UPRMSTP9LCADE', 'UHRMQQ7KETPCS'];

  return [users[Math.floor(Math.random() * users.length)]];
}

export class ScheduleStore extends BaseStore {
  @observable
  searchResult: { [key: string]: Array<Schedule['id']> } = {};

  @observable.shallow
  items: { [id: string]: Schedule } = {};

  @observable.shallow
  rotations: {
    [id: string]: {
      [startMoment: string]: Rotation;
    };
  } = {};

  @observable.shallow
  events: {
    [scheduleId: string]: {
      [type: string]: {
        [startMoment: string]: Events['events'];
      };
    };
  } = {};

  @observable
  scheduleToScheduleEvents: {
    [id: string]: ScheduleEvent[];
  } = {};

  @observable
  byDayOptions: SelectOption[];

  constructor(rootStore: RootStore) {
    super(rootStore);

    this.path = '/schedules/';
  }

  @action
  async updateScheduleEvents(
    scheduleId: Schedule['id'],
    withEmpty: boolean,
    with_gap: boolean,
    date: string,
    user_tz: string
  ) {
    const { events } = await makeRequest(`/schedules/${scheduleId}/events/`, {
      params: { date, user_tz, with_empty: withEmpty, with_gap: with_gap },
    });

    this.scheduleToScheduleEvents = {
      ...this.scheduleToScheduleEvents,
      [scheduleId]: events,
    };
  }

  @action
  async updateItems(query = '') {
    const result = await this.getAll();

    this.items = {
      ...this.items,
      ...result.reduce(
        (acc: { [key: number]: Schedule }, item: Schedule) => ({
          ...acc,
          [item.id]: item,
        }),
        {}
      ),
    };

    this.searchResult = {
      ...this.searchResult,
      [query]: result.map((item: Schedule) => item.id),
    };
  }

  async updateItem(id: Schedule['id']) {
    if (id) {
      const item = await this.getById(id);

      this.items = {
        ...this.items,
        [item.id]: item,
      };
    }
  }

  getSearchResult(query = '') {
    if (!this.searchResult[query]) {
      return undefined;
    }

    return this.searchResult[query].map((scheduleId: Schedule['id']) => this.items[scheduleId]);
  }

  @action
  async reloadIcal(scheduleId: Schedule['id']) {
    await makeRequest(`/schedules/${scheduleId}/reload_ical/`, {
      method: 'POST',
    });
  }

  async getICalLink(scheduleId: Schedule['id']) {
    return await makeRequest(`/schedules/${scheduleId}/export_token/`, {
      method: 'GET',
    });
  }

  async createICalLink(scheduleId: Schedule['id']) {
    return await makeRequest(`/schedules/${scheduleId}/export_token/`, {
      method: 'POST',
    });
  }

  async deleteICalLink(scheduleId: Schedule['id']) {
    await makeRequest(`/schedules/${scheduleId}/export_token/`, {
      method: 'DELETE',
    });
  }

  // ------- NEW SCHEDULES API ENDPOINTS ---------

  async createRotation(scheduleId: Schedule['id'], isOverride: boolean, params: any) {
    const type = isOverride ? 3 : 2;

    return await makeRequest(`/oncall_shifts/`, {
      data: { type, schedule: scheduleId, ...params },
      method: 'POST',
    });
  }

  async updateRotation(rotationId: Rotation['id']) {
    return await makeRequest(`/oncall_shifts/`, {
      params: { shift_id: rotationId },
      method: 'GET',
    });
  }

  async updateRotationMock(rotationId: Rotation['id'], fromString: string, currentTimezone: Timezone) {
    if (this.rotations[rotationId]?.[fromString]) {
      return;
    }

    const response = await new Promise((resolve, reject) => {
      setTimeout(() => {
        if (!fromString) {
          fromString = dayjs().startOf('week').format('YYYY-MM-DDTHH:mm:ss.000Z');
        }

        let startMoment = dayjs(fromString);
        const utcOffset = dayjs().tz(currentTimezone).utcOffset();

        startMoment = startMoment.add(utcOffset, 'minutes');
        //const startMoment = dayjs().utc().startOf('week');

        const shifts = [];
        for (let i = 0; i < 7; i++) {
          const shiftDuration = (12 + Math.floor(Math.random() * 12)) * 60 * 60;
          const gapDuration = 24 * 60 * 60 - shiftDuration;

          shifts.push({
            pk: I++,
            start: startMoment.add(24 * i, 'hour'),
            duration: shiftDuration,
            users: getUsers(),
          });

          shifts.push({
            pk: I++,
            start: startMoment.add(24 * i, 'hour').add(shiftDuration, 'seconds'),
            duration: gapDuration,
            is_gap: true,
          });
        }

        resolve({ id: rotationId, shifts });
      }, 500);
    });

    this.rotations = {
      ...this.rotations,
      [rotationId]: {
        ...this.rotations[rotationId],
        [fromString]: response as Rotation,
      },
    };
  }

  async updateOncallShifts(scheduleId: Schedule['id']) {
    return await makeRequest(`/oncall_shifts/`, {
      params: {
        schedule: scheduleId,
      },
      method: 'GET',
    });
  }
  async updateEvents(scheduleId: Schedule['id'], fromString: string, type: RotationType = 'rotation', days = 7) {
    const response = await makeRequest(`/schedules/${scheduleId}/filter_events/`, {
      params: {
        type,
        date: fromString,
        days,
      },
      method: 'GET',
    });

    const events = type !== 'final' ? fillGaps(response.events) : response.events;

    const shifts: { [key: string]: Event[] } = {};

    for (const [i, event] of response.events.entries()) {
      if (event.shift?.pk) {
        if (!shifts[event.shift.pk]) {
          shifts[event.shift.pk] = [];
        }
        shifts[event.shift.pk].push(event);
      }
    }

    const shiftsArr = Object.keys(shifts).map((key) => {
      return fillGaps(shifts[key]);
    });

    console.log(type, shifts);

    this.events = {
      ...this.events,
      [scheduleId]: {
        ...this.events[scheduleId],
        [type]: {
          ...this.events[scheduleId]?.[type],
          [fromString]: shiftsArr,
        },
      },
    };

    console.log(toJS(this.events));

    /*this.rotations = {
      ...this.rotations,
      [rotationId]: {
        ...this.rotations[rotationId],
        [level]: {
          [fromString]: response as Rotation,
        },
      },
    };*/
  }

  async updateFrequencyOptions() {
    return await makeRequest(`/oncall_shifts/frequency_options/`, {
      method: 'GET',
    });
  }

  async updateDaysOptions() {
    this.byDayOptions = await makeRequest(`/oncall_shifts/days_options/`, {
      method: 'GET',
    });
  }
}
