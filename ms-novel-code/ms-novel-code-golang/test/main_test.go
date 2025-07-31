
package core

import (
	"testing"

	"github.com/stretchr/testify/require"
)

// 1. Empty tree should yield an empty slice.
func TestRowWiseMaxEmptyTree(t *testing.T) {
	got := rowWiseMax(nil)
	require.NotNil(t, got)
	require.Empty(t, got["output"])
}

// 2. Single-node tree.
func TestRowWiseMaxSingleNode(t *testing.T) {
	root := &Node{Val: 42}
	want := []int{42}

	got := rowWiseMax(root)
	require.Equal(t, want, got["output"])
}

// 3. Complete two-level tree.
func TestRowWiseMaxTwoLevelComplete(t *testing.T) {
	root := &Node{Val: 5}
	root.Left = &Node{Val: 2}
	root.Right = &Node{Val: 7}
	want := []int{5, 7}

	got := rowWiseMax(root)
	require.Equal(t, want, got["output"])
}

// 4. Tree with all negative numbers.
func TestRowWiseMaxNegativeValues(t *testing.T) {
	root := &Node{Val: -1}
	root.Left = &Node{Val: -2}
	root.Right = &Node{Val: -3}
	want := []int{-1, -2}

	got := rowWiseMax(root)
	require.Equal(t, want, got["output"])
}

// 5. Duplicate values across a level.
func TestRowWiseMaxDuplicateValues(t *testing.T) {
	root := &Node{Val: 5}
	root.Left = &Node{Val: 5}
	root.Right = &Node{Val: 5}
	want := []int{5, 5}

	got := rowWiseMax(root)
	require.Equal(t, want, got["output"])
}

// 6. Left-skewed (linked-list-like) tree.
func TestRowWiseMaxLeftSkewed(t *testing.T) {
	root := &Node{Val: 3}
	root.Left = &Node{Val: 4}
	root.Left.Left = &Node{Val: 10}
	want := []int{3, 4, 10}

	got := rowWiseMax(root)
	require.Equal(t, want, got["output"])
}

// 7. Right-skewed tree.
func TestRowWiseMaxRightSkewed(t *testing.T) {
	root := &Node{Val: 3}
	root.Right = &Node{Val: 1}
	root.Right.Right = &Node{Val: 0}
	want := []int{3, 1, 0}

	got := rowWiseMax(root)
	require.Equal(t, want, got["output"])
}

// 8. Deeper tree where the max is on a left grand-child.
func TestRowWiseMaxDeepTree(t *testing.T) {
	root := &Node{Val: 1}
	root.Left = &Node{Val: 2}
	root.Right = &Node{Val: 3}
	root.Left.Left = &Node{Val: 8}
	root.Left.Right = &Node{Val: 4}
	root.Right.Right = &Node{Val: 5}
	want := []int{1, 3, 8}

	got := rowWiseMax(root)
	require.Equal(t, want, got["output"])
}

// 9. Max value appears on the right-most node of the deepest level.
func TestRowWiseMaxMaxOnRightmost(t *testing.T) {
	root := &Node{Val: 10}
	root.Left = &Node{Val: 5}
	root.Right = &Node{Val: 12}
	root.Left.Left = &Node{Val: 20}
	root.Right.Right = &Node{Val: 25}
	want := []int{10, 12, 25}

	got := rowWiseMax(root)
	require.Equal(t, want, got["output"])
}

// 10. Larger mixed-value tree to stress-test breadth traversal.
func TestRowWiseMaxLargeTree(t *testing.T) {
	root := &Node{Val: 100}
	root.Left = &Node{Val: 200}
	root.Right = &Node{Val: -50}
	root.Left.Left = &Node{Val: 70}
	root.Left.Right = &Node{Val: 90}
	root.Right.Left = &Node{Val: 0}
	root.Right.Right = &Node{Val: 300}
	want := []int{100, 200, 300}

	got := rowWiseMax(root)
	require.Equal(t, want, got["output"])
}