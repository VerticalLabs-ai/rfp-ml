import React from 'react'
import { LucideIcon } from 'lucide-react'

interface StatsCardProps {
  title: string
  value: string | number
  icon: LucideIcon
  trend?: {
    value: string
    positive: boolean
  }
  highlight?: boolean
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'red'
}

export default function StatsCard({ title, value, icon: Icon, trend, highlight, color = 'blue' }: StatsCardProps) {
  const colorClasses = {
    blue: 'from-blue-500 to-blue-600',
    green: 'from-green-500 to-green-600',
    purple: 'from-purple-500 to-purple-600',
    orange: 'from-orange-500 to-orange-600',
    red: 'from-red-500 to-red-600'
  }

  const iconBgClasses = {
    blue: 'bg-blue-100 dark:bg-blue-900/20',
    green: 'bg-green-100 dark:bg-green-900/20',
    purple: 'bg-purple-100 dark:bg-purple-900/20',
    orange: 'bg-orange-100 dark:bg-orange-900/20',
    red: 'bg-red-100 dark:bg-red-900/20'
  }

  const iconColorClasses = {
    blue: 'text-blue-600 dark:text-blue-400',
    green: 'text-green-600 dark:text-green-400',
    purple: 'text-purple-600 dark:text-purple-400',
    orange: 'text-orange-600 dark:text-orange-400',
    red: 'text-red-600 dark:text-red-400'
  }

  return (
    <div className={`
      relative overflow-hidden
      bg-white dark:bg-gray-800
      rounded-xl shadow-lg hover:shadow-xl
      transition-all duration-300 hover:-translate-y-1
      border border-gray-100 dark:border-gray-700
      ${highlight ? 'ring-2 ring-yellow-400 dark:ring-yellow-500' : ''}
    `}>
      {/* Gradient accent bar */}
      <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${colorClasses[color]}`} />

      <div className="px-6 py-5">
        <div className="flex items-center">
          <div className={`
            flex-shrink-0 rounded-lg p-3
            ${iconBgClasses[color]}
          `}>
            <Icon className={`w-6 h-6 ${iconColorClasses[color]}`} />
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                {title}
              </dt>
              <dd className="flex items-baseline mt-1">
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {value}
                </div>
                {trend && (
                  <div className={`
                    ml-2 flex items-baseline text-sm font-semibold
                    ${trend.positive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
                  `}>
                    <span>{trend.positive ? '↑' : '↓'}</span>
                    <span className="ml-0.5">{trend.value}</span>
                  </div>
                )}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}
