import {
  ensureArray,
  ensureInteger,
  ensureString,
} from '@baserow/modules/core/utils/validator'
import { expect } from '@jest/globals'

describe('ensureInteger', () => {
  it('should return the value as an integer if it is already an integer', () => {
    expect(ensureInteger(5)).toBe(5)
    expect(ensureInteger(-10)).toBe(-10)
  })

  it('should convert a string representation of an integer to an integer', () => {
    expect(ensureInteger('15')).toBe(15)
    expect(ensureInteger('-20')).toBe(-20)
  })

  it('should throw an error if the value is not a valid integer', () => {
    expect(() => ensureInteger('abc')).toThrow(Error)
    expect(() => ensureInteger('12.34')).toThrow(Error)
    expect(() => ensureInteger(true)).toThrow(Error)
    expect(() => ensureInteger(null)).toThrow(Error)
    expect(() => ensureInteger([])).toThrow(Error)
  })
})

describe('ensureString', () => {
  it('should return an empty string if the value is falsy', () => {
    expect(ensureString(null)).toBe('')
    expect(ensureString(undefined)).toBe('')
    expect(ensureString('')).toBe('')
    expect(ensureString([])).toBe('')
  })

  it('should convert the value to a string if it is truthy', () => {
    expect(ensureString(5)).toBe('5')
    expect(ensureString(true)).toBe('true')
    expect(ensureString(0)).toBe('0')
    expect(ensureString(false)).toBe('false')
    expect(ensureString([1, 2, 3])).toBe('1,2,3')
    expect(ensureString([[], [[], [5, 7], 6]])).toBe('5,7,6')
    expect(ensureString({ key: 'value' })).toBe('[object Object]')
  })
})

describe('ensureArray', () => {
  it('should return an empty array if the value is falsy', () => {
    expect(ensureArray(null)).toStrictEqual([])
    expect(ensureArray('')).toStrictEqual([])
    expect(ensureArray([])).toStrictEqual([])
    expect(ensureArray([[[]]])).toStrictEqual([[[]]])
  })
  it('should raise an error for empty values when allowEmpty is not set', () => {
    const error = new Error('A non empty value is required.')
    expect(() => ensureArray(null, { allowEmpty: false })).toThrow(error)
    expect(() => ensureArray('', { allowEmpty: false })).toThrow(error)
    expect(() => ensureArray([], { allowEmpty: false })).toThrow(error)
  })
  it('should convert the value to an array if it is truthy', () => {
    expect(ensureArray(5)).toStrictEqual([5])
    expect(ensureArray(true)).toStrictEqual([true])
    expect(ensureArray(0)).toStrictEqual([0])
    expect(ensureArray(false)).toStrictEqual([false])
    expect(ensureArray('one,two,three')).toStrictEqual(['one', 'two', 'three'])
    expect(ensureArray('one,two,,')).toStrictEqual(['one', 'two', '', ''])
    expect(ensureArray([1, 2, 3])).toStrictEqual([1, 2, 3])
    expect(ensureArray({ key: 'value' })).toStrictEqual([{ key: 'value' }])
  })
})
